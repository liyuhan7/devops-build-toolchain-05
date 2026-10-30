"""命令行入口。

  python3 -m buildchecker version
  python3 -m buildchecker smoke [--fixture fixtures/md-rd]

E4 只提供 version 与 smoke 两个子命令；E6 再加入真正的检测命令（例如 full-check）。
"""
import argparse
import json

from . import __version__
from .smoke import run_smoke


def build_parser():
    ap = argparse.ArgumentParser(prog="buildchecker")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("version", help="打印版本")
    sp = sub.add_parser("smoke", help="E4 冒烟测试：在容器里用 strace 跟踪 E3 md-rd 样例")
    sp.add_argument("--fixture", default="fixtures/md-rd")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.cmd == "version":
        print(f"buildchecker {__version__}")
        return 0
    result = run_smoke(args.fixture)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1
