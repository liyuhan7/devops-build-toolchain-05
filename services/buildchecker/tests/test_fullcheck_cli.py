"""区分检测状态、发现门禁和命令行退出码。"""
import json
import pytest
from buildchecker import cli


@pytest.mark.parametrize("status,findings,gated,expected", [
    ("SUCCEEDED", [], True, 0),
    ("SUCCEEDED", [{"type": "MISSING"}], True, 1),
    ("SUCCEEDED", [{"type": "MISSING"}], False, 0),
    ("FAILED", [], False, 1),
])
def test_detection_status_and_findings_control_exit_code(monkeypatch, capsys, status, findings, gated, expected):
    report = {"status": status, "findings": findings}
    monkeypatch.setattr(cli, "full_check", lambda *args: report)
    args = ["full-check", "--out", "unused-in-offline-test"]
    if gated:
        args.append("--fail-on-findings")
    assert cli.main(args) == expected
    assert json.loads(capsys.readouterr().out) == report


def test_request_passes_exact_commands_environment_trace_and_total_budget(monkeypatch, tmp_path):
    config = {"clean_command": ["make", "clean"], "build_command": ["make", "app"],
              "timeout_seconds": 17, "environment": {"CFLAGS": "-O0 -g"}}
    path = tmp_path / "request.json"
    path.write_text(json.dumps({"configuration": config, "trace_id": "same-chain"}))
    captured = {}

    def collect(*args, **kwargs):
        captured.update(args=args, kwargs=kwargs)
        return {"status": "SUCCEEDED", "findings": []}

    monkeypatch.setattr(cli, "full_check", collect)
    assert cli.main(["full-check", "--out", "unused", "--request", str(path)]) == 0
    assert captured["args"][2:] == (config["clean_command"], config["build_command"], 17)
    assert captured["kwargs"] == {"trace_id": "same-chain", "environment": config["environment"]}
