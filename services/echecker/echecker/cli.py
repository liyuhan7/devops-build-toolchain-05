"""对课程受限项目执行全量或历史图驱动的依赖扫描。"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from .core import save, scan


def main(argv=None):
    parser = argparse.ArgumentParser(prog="echecker")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.out.exists():
            raise ValueError("OUTPUT_MUST_BE_NEW")
        old = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline else None
        result = scan(args.project, old)
        save(args.out, result)
        print(json.dumps({"status": "SUCCEEDED", "report": str(args.out),
                          "reused": result["reused"], "refreshed": result["refreshed"]}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1
