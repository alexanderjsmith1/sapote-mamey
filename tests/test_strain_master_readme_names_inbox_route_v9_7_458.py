"""The top README a new strain master gets must name the route the code allows: submit, then
verify by a different id, then apply. `store` is refused unless the master opts into
"direct_store", so the README must not call it the one way in."""
from mamey import strain_master


def test_top_readme_names_inbox_route_not_store():
    text = strain_master._top_readme("Example master")
    assert "strain-master submit" in text and "apply" in text
    assert "only through `python mamey_run.py strain-master store`" not in text
