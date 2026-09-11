"""Completion markers must not survive a partial widget refresh."""
import json
import pytest
from mamey import widget_deliverable as widgets

@pytest.mark.parametrize('failure', ['priority.html', 'publication_metadata.json', 'SHA256SUMS.txt'])
def test_failed_refresh_removes_completion_markers(tmp_path, monkeypatch, failure):
    package=tmp_path/'package'; package.mkdir()
    (package/'manifest.json').write_text(json.dumps({'strain_id':'TEST','package_status':'MAMEY_COMPLETE'}))
    output=tmp_path/'widgets'
    widgets.render_widget_deliverable(package, output)
    assert (output/'WIDGET_MANIFEST.json').is_file()
    original=widgets._atomic_write_text
    def fail(path, text):
        if path.name==failure:
            raise OSError('injected write failure')
        return original(path,text)
    monkeypatch.setattr(widgets,'_atomic_write_text',fail)
    with pytest.raises(OSError, match='injected write failure'):
        widgets.render_widget_deliverable(package,output)
    assert not (output/'WIDGET_MANIFEST.json').exists()
    assert not (output/'SHA256SUMS.txt').exists()
    monkeypatch.setattr(widgets,'_atomic_write_text',original)
    result=widgets.render_widget_deliverable(package,output)
    assert result['status']=='PASS'
    assert (output/'SHA256SUMS.txt').is_file()
