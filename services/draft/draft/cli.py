"""命令行入口。

  python3 -m draft version
  python3 -m draft smoke [--fixture fixtures/draft]

E4 只提供 version 与 smoke 两个子命令；E6 再加入真正的生成命令（例如 generate）。
"""
import argparse
import json

from . import __version__
from .smoke import run_smoke


def build_parser():
    ap = argparse.ArgumentParser(prog="draft")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("version", help="打印版本")
    sp = sub.add_parser("smoke", help="E4 冒烟测试：在容器里通过宿主机 Docker 构建 E3 的 Dockerfile.broken")
    sp.add_argument("--fixture", default="fixtures/draft")
    sp.add_argument("--tag", default="e4-smoke-broken:latest")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.cmd == "version":
        print(f"draft {__version__}")
        return 0
    result = run_smoke(args.fixture, args.tag)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1
