"""v9.7.101 P1: the ChatGPT execution prompt must not hardcode a master-workbook
engine version (it silently rots on every engine bump and sends the operator
looking for the wrong filename — the multi-strain data-loss footgun).

Ties the doc to the code: the prompt's described pattern must match what
mamey/cli.py actually emits (`Mamey_v{__version__}_Master_After_{strain}_{date}.xlsx`).
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPT = ROOT / "prompts" / "MAMEY_CHATGPT_EXECUTION_PROMPT.md"
CLI = ROOT / "mamey" / "cli.py"


def test_no_hardcoded_master_version_in_exec_prompt():
    text = PROMPT.read_text()
    # No literal Mamey_v1.9.<NN>_Master or Mamey_v9.<...>_Master with a pinned number.
    hits = re.findall(r"Mamey_v\d+\.\d+(?:\.\d+)?_Master", text)
    assert not hits, f"hardcoded master-workbook version(s) in exec prompt: {hits}"


def test_exec_prompt_uses_version_agnostic_glob():
    text = PROMPT.read_text()
    assert "Mamey_v*_Master_After" in text, (
        "exec prompt should describe the master workbook with a version-agnostic glob"
    )


def test_cli_emits_versioned_master_name():
    # Guard the assumption the prompt rests on: cli.py stamps the engine version
    # into the master name, which is why the prompt must use a glob, not a literal.
    cli = CLI.read_text()
    assert "Master_After_" in cli and "__version__" in cli, (
        "cli.py master-workbook naming changed — re-check the exec-prompt guidance"
    )
