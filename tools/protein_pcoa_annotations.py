"""Conservative disclosure for saved-coordinate consumers without native-chain admission."""
import math


def supplied_axis_annotations(run):
    values = run.get("pct_axes")
    if values is not None:
        if not isinstance(values, list) or len(values) < 2 or any(isinstance(v, bool) for v in values):
            raise ValueError("pct_axes must contain at least two finite numeric annotations")
        try:
            values = [float(v) for v in values]
        except (TypeError, ValueError) as exc:
            raise ValueError("pct_axes must contain at least two finite numeric annotations") from exc
        if not all(math.isfinite(v) for v in values):
            raise ValueError("pct_axes must contain at least two finite numeric annotations")
    disclosure = ("Supplied axis percentage annotations: definition and historical fit execution are unverified; "
                  "not variance explained. Values are retained without clipping or renormalization. "
                  "This consumer replays saved coordinates and executes no ordination fit."
                  if values is not None else
                  "Axis percentage annotations were not provided. Historical axis definition and fit execution "
                  "are unverified. This consumer replays saved coordinates and executes no ordination fit.")
    return dict(state="AVAILABLE" if values is not None else "NOT_PROVIDED", pct_axes=values,
                definition=dict(state="SUPPLIED_UNVERIFIED", name=None),
                fit_execution="UNVERIFIED_SUPPLIED_METADATA", consumer_fit_execution="NOT_EXECUTED",
                disclosure=disclosure)


def supplied_axis_label(annotations, axis):
    values = annotations.get("pct_axes") or []
    return f"PCoA {axis + 1}" + (f" ({values[axis]:.1f}% supplied)" if axis < len(values) else "")
