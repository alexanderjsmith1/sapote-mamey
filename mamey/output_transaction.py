"""Stage a complete fresh tool-output set; roll back owned links on ordinary failure.

Requires stable inputs and no uncooperating output writer. Flat-file publication is
not crash-atomic; a killed process may leave a partial set. Existing files are never
replaced and rollback checks inode ownership before removing anything.
"""
from __future__ import annotations
from contextlib import contextmanager
import os
import shutil
import stat
from pathlib import Path, PurePosixPath
import tempfile


def _paths(root, names):
    result=[]
    for name in names:
        rel=PurePosixPath(name)
        if rel.is_absolute() or any(x in ('','.', '..') for x in rel.parts) or '\\' in name:
            raise ValueError('invalid output relative path')
        target=root.joinpath(*rel.parts)
        if target.resolve() != target.absolute() or target.exists() or target.is_symlink():
            raise ValueError('tool output must be fresh and must not use a symlink: '+str(target))
        result.append(target)
    if len({str(x).casefold() for x in result}) != len(result):
        raise ValueError('output names collide ignoring case')
    return result


def _record_cleanup(primary, row):
    diagnostics = getattr(primary, "rollback_cleanup_diagnostics", None)
    if diagnostics is None:
        diagnostics = []
        primary.rollback_cleanup_diagnostics = diagnostics
    diagnostics.append(row)
    if row["status"] != "REMOVED":
        detail = row.get("error_message", "")
        primary.add_note(f"Rollback {row['action']}: {row['status']} at {row['path']}" +
                         (f" ({detail})" if detail else ""))


def _rollback_owned(primary, entries, *, directories=False):
    """Try every owned cleanup, attaching diagnostics to the primary failure.

    A missing path is an expected rollback outcome. A replaced inode belongs to
    another writer. Neither is removed; both remain explicit in the exception's
    cleanup ledger. Unexpected cleanup errors never replace the publication fault.
    """
    action = "rmdir" if directories else "unlink"
    for path, owned in reversed(entries):
        row = {"path": str(path), "action": action,
               "owned_device": owned.st_dev, "owned_inode": owned.st_ino}
        try:
            actual = path.lstat()
            if (actual.st_dev, actual.st_ino) != (owned.st_dev, owned.st_ino):
                row.update(status="OWNERSHIP_CHANGED", actual_device=actual.st_dev,
                           actual_inode=actual.st_ino)
            else:
                path.rmdir() if directories else path.unlink()
                row["status"] = "REMOVED"
        except FileNotFoundError:
            row["status"] = "MISSING"
        except Exception as cleanup_error:
            row.update(status="CLEANUP_FAILED", error_type=type(cleanup_error).__name__,
                       error_message=str(cleanup_error))
        _record_cleanup(primary, row)


@contextmanager
def fresh_output_set(outdir, names):
    root=Path(outdir).resolve()
    names=list(names)
    if root.exists() and not root.is_dir():raise ValueError('output root must be a directory')
    _paths(root,names)
    root.parent.mkdir(parents=True,exist_ok=True)
    # Explicit ownership avoids TemporaryDirectory finalizer teardown masking a
    # primary failure or later cleaning an independent replacement directory.
    stage=Path(tempfile.mkdtemp(prefix='.mamey-output-',dir=root.parent))
    stage_owned=stage.lstat()
    primary=None
    published=[]
    try:
        yield stage
        found=[]
        for directory, dirs, files in os.walk(stage, onerror=lambda error: (_ for _ in ()).throw(error)):
            for name in dirs+files:
                if (Path(directory)/name).is_symlink():raise ValueError('staged output must not be a symlink')
            found.extend((Path(directory)/name).relative_to(stage).as_posix() for name in files)
        if set(found)!=set(names):raise ValueError('staged tool output set is incomplete or unexpected')
        final=_paths(root,names)
        directories=[];published=[]
        try:
            if not root.exists():
                root.mkdir();directories.append((root,root.stat()))
            for source,target in zip((stage/name for name in names),final):
                parents=[];parent=target.parent
                while parent!=root and not parent.exists():parents.append(parent);parent=parent.parent
                for parent in reversed(parents):
                    parent.mkdir();directories.append((parent,parent.stat()))
                source_owned=source.stat()
                os.link(source,target)
                published.append((target,source_owned))
        except Exception as primary:
            _rollback_owned(primary, published)
            _rollback_owned(primary, directories, directories=True)
            raise
    except BaseException as failure:
        primary=failure
        raise
    finally:
        cleanup_row={"path":str(stage), "action":"staging_rmtree",
                     "owned_device":stage_owned.st_dev, "owned_inode":stage_owned.st_ino}
        cleanup_attempted=False
        try:
            actual=stage.lstat()
            if (not stat.S_ISDIR(actual.st_mode) or
                    (actual.st_dev,actual.st_ino)!=(stage_owned.st_dev,stage_owned.st_ino)):
                cleanup_row.update(status="OWNERSHIP_CHANGED",actual_device=actual.st_dev,
                                   actual_inode=actual.st_ino)
                raise RuntimeError('owned staging directory changed; replacement preserved')
            cleanup_attempted=True
            shutil.rmtree(stage)
            cleanup_row["status"]="REMOVED"
        except Exception as cleanup_error:
            if isinstance(cleanup_error,FileNotFoundError) and not cleanup_attempted:
                cleanup_row["status"]="MISSING"
                if primary is not None:
                    _record_cleanup(primary,cleanup_row)
            else:
                cleanup_row.setdefault("status","CLEANUP_FAILED")
                cleanup_row.update(error_type=type(cleanup_error).__name__,error_message=str(cleanup_error))
                if primary is not None:
                    _record_cleanup(primary,cleanup_row)
                else:
                    # Publication completed, but cleanup did not. Keep the linked
                    # outputs, fail honestly, and expose their creation journal.
                    cleanup_error.output_transaction_published_paths=[str(path) for path,_ in published]
                    _record_cleanup(cleanup_error,cleanup_row)
                    cleanup_error.add_note('Output links were published and retained: '+
                                           ', '.join(cleanup_error.output_transaction_published_paths))
                    raise



def publish_payloads(payloads):
    """Publish fully serialized byte payloads at fresh paths; ordinary-fault rollback.

    Parents must exist. Caller preflights the whole roster before computation.
    A crash can leave partial files; this is not an atomic cross-directory commit.
    """
    payloads={Path(path):data for path,data in payloads.items()}
    if any(not isinstance(data,bytes) for data in payloads.values()):raise ValueError('payloads must be serialized bytes')
    if any(p.exists() or p.is_symlink() or not p.parent.is_dir() for p in payloads):
        raise ValueError('all output paths must be fresh with existing parents')
    published=[]
    try:
        for path,data in payloads.items():
            with path.open('xb') as handle:
                owned=os.fstat(handle.fileno())
                published.append((path,owned))
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
    except Exception as primary:
        _rollback_owned(primary, published)
        raise
