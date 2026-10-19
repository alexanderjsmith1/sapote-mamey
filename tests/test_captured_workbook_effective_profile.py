"""Requested/effective workbook declarations must match the existing forced consumer."""
import json
import pytest
try:
    from .test_captured_actual_run import inputs, run_args
except ImportError:
    from test_captured_actual_run import inputs, run_args
from mamey import cli, captured_run, capture_completion
from mamey.intake_session import CapturedIntakeHold, encode


@pytest.mark.parametrize("requested", [False, True])
@pytest.mark.parametrize("capped", [False, True])
def test_resolved_bound_and_serialized_workbook_flag_matches_private_execution(inputs, tmp_path, requested, capped):
    args = cli.build_parser().parse_args(run_args(inputs, tmp_path))
    args.require_workbook = requested
    args.chatgpt_safe = capped
    selected = captured_run.resolve_execution(args)
    policy = captured_run.load_policy(args.capture_policy)
    capture_completion.bind_governance(selected, policy)
    session, genbank, aliases = captured_run.capture(selected, policy)
    frame = captured_run.RunFrame(session, args.input_zip, tmp_path / "stage", tmp_path / "final", None, None, aliases)
    frame.genbank = genbank
    identity = capture_completion.binding(selected, policy, [])
    execution = identity["execution_options"]
    assert args.require_workbook is requested
    assert execution["requested"]["require_workbook"] is requested
    assert execution["effective"]["require_workbook"] is True
    observed = []
    def consumer(private):
        observed.append(private.require_workbook)
        serialized = json.loads(encode(frame.receipt()))
        assert serialized["execution_options"] == execution
        return 0
    captured_run.execute_stage(selected, consumer, frame)
    assert observed == [True]


def test_required_workbook_failure_still_refuses(inputs, tmp_path):
    args = captured_run.resolve_execution(cli.build_parser().parse_args(run_args(inputs, tmp_path)))
    policy = captured_run.load_policy(args.capture_policy)
    capture_completion.bind_governance(args, policy)
    session, genbank, aliases = captured_run.capture(args, policy)
    frame = captured_run.RunFrame(session, args.input_zip, tmp_path / "stage", tmp_path / "final", None, None, aliases)
    frame.genbank = genbank
    def refused(private):
        assert private.require_workbook is True
        return 2
    with pytest.raises(CapturedIntakeHold, match="PIPELINE_NOT_SUCCESSFUL"):
        captured_run.execute_stage(args, refused, frame)
