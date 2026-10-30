"""BuildChecker 的版本、环境冒烟与全量检测入口。"""
import argparse
import json
from pathlib import Path

from . import __version__
from .smoke import run_smoke
from .fullcheck import full_check


def build_parser():
    ap = argparse.ArgumentParser(prog="buildchecker")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("version", help="打印版本")
    sp = sub.add_parser("smoke", help="E4 冒烟测试：在容器里用 strace 跟踪 E3 md-rd 样例")
    sp.add_argument("--fixture", default="fixtures/md-rd")
    full = sub.add_parser("full-check", help="跟踪 GNU Make 并比较实际与声明依赖")
    full.add_argument("--fixture", default="fixtures/md-rd")
    full.add_argument("--out", required=True)
    full.add_argument("--clean-command", default="make clean")
    full.add_argument("--build-command", default="make app")
    full.add_argument("--timeout", type=int, default=120)
    full.add_argument("--fail-on-findings", action="store_true")
    full.add_argument("--request", help="由公共交接入口提供的完整请求；覆盖命令、环境、trace 和总预算")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.cmd == "version":
        print(f"buildchecker {__version__}")
        return 0
    if args.cmd == "full-check":
        try:
            if args.timeout <= 0:
                raise ValueError("Timeout must be positive")
            if args.request:
                # 公共运行入口在宿主验证请求；采集进程只依赖标准库。
                request = json.loads(Path(args.request).read_text(encoding="utf-8"))
                config = request["configuration"]
                result = full_check(args.fixture, args.out, config["clean_command"], config["build_command"],
                                    config["timeout_seconds"], trace_id=request["trace_id"], environment=config["environment"])
            else:
                result = full_check(args.fixture, args.out, args.clean_command, args.build_command, args.timeout)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            print(json.dumps({"status": "FAILED", "error": str(exc)}, ensure_ascii=False))
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "SUCCEEDED" and not (args.fail_on_findings and result["findings"]) else 1
    result = run_smoke(args.fixture)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1
