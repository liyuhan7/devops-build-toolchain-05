"""验证 clean/build 总预算以及失败阶段，不要求本机有 Linux 工具链。"""
from types import SimpleNamespace

import pytest

from buildchecker import fullcheck


@pytest.fixture
def collection(tmp_path, monkeypatch):
    source = tmp_path / "fixture"
    source.mkdir()
    (source / "Makefile").write_text("app:\n\tfalse\n")
    # 仅替换模块的平台检查；路径和真实文件操作仍使用宿主平台。
    monkeypatch.setattr(fullcheck, "os", SimpleNamespace(name="posix"))
    return source, tmp_path / "out"


def test_clean_and_build_share_one_timeout_budget(collection, monkeypatch):
    clock = [100.0]
    budgets = []
    monkeypatch.setattr(fullcheck.time, "monotonic", lambda: clock[0])

    def execute(argv, cwd, stdout, stderr, timeout, environment):
        budgets.append(timeout)
        if len(budgets) == 1:
            clock[0] += 6
            return 0
        raise TimeoutError("test budget exhausted")

    monkeypatch.setattr(fullcheck, "execute", execute)
    report = fullcheck.full_check(*collection, timeout=10)
    assert budgets == [10, 4]
    assert report["status"] == "TIMED_OUT"
    assert report["public_error_code"] == "BUILD_TIMEOUT" and report["error_phase"] == "BUILD"


@pytest.mark.parametrize("clean_code,build_code,expected,phase", [(2, 0, "CLEAN_FAILED", "CLEAN"),
    (0, 2, "BUILD_FAILED", "BUILD")])
def test_nonzero_command_reports_its_real_phase(collection, monkeypatch, clean_code, build_code, expected, phase):
    codes = iter([clean_code, build_code])
    monkeypatch.setattr(fullcheck, "execute", lambda *args: next(codes))
    report = fullcheck.full_check(*collection)
    assert report["status"] == "FAILED" and report["findings"] == []
    assert report["public_error_code"] == expected and report["error_phase"] == phase


def test_missing_strace_is_execution_failure(collection, monkeypatch):
    def execute(argv, *args):
        if argv[0] == "strace":
            raise FileNotFoundError("strace")
        return 0
    monkeypatch.setattr(fullcheck, "execute", execute)
    report = fullcheck.full_check(*collection)
    assert report["public_error_code"] == "TRACE_FAILED" and report["error_phase"] == "TRACE"
