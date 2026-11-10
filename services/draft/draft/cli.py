"""DRAFT 服务的教学命令行入口。"""
import argparse
import json

from . import __version__
from .autobuild import auto_build
from .smoke import run_smoke


def build_parser():
    ap = argparse.ArgumentParser(prog="draft")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("version", help="显示服务版本")
    sp = sub.add_parser("smoke", help="检查 Docker socket 和预期的缺少 make 故障")
    sp.add_argument("--fixture", default="fixtures/draft")
    sp.add_argument("--tag", default="e4-smoke-broken:latest")
    sp = sub.add_parser("auto-build", help="重放人工候选的两轮构建与程序验证")
    sp.add_argument("--fixture", default="fixtures/draft")
    sp.add_argument("--candidate", required=True)
    sp.add_argument("--out", required=True)
    sp.add_argument("--expected-output", required=True)
    sp.add_argument("--timeout", type=int, default=600)
    sp.add_argument("--verify-timeout", type=int, default=30)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.cmd == "version":
        print(f"draft {__version__}")
        return 0
    if args.cmd == "smoke":
        result = run_smoke(args.fixture, args.tag)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["passed"] else 1
    try:
        result = auto_build(args.fixture, args.candidate, args.out,
                            args.expected_output, args.timeout, args.verify_timeout)
    except (ValueError, OSError) as exc:
        result = {"status": "FAILED", "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "SUCCEEDED" else 1
