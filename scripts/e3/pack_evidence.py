"""合并运行证据的命令输出，并按字节索引读取原始输出。"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

from run_c0 import write_json

ROOT = Path(__file__).resolve().parents[2]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_stream(directory, command, stream):
    path = (directory / command[stream]).resolve()
    if not path.is_relative_to(directory.resolve()):
        raise ValueError("日志路径超出证据目录")
    data = path.read_bytes()
    span = command.get(stream + "_range")
    if span is None:
        return data
    start, length = span["offset"], span["length"]
    if start < 0 or length < 0 or start + length > len(data):
        raise ValueError("日志字节范围无效")
    data = data[start:start + length]
    if digest(data) != span["sha256"]:
        raise ValueError("日志输出摘要不一致")
    return data


def prepare_group(directory, operator):
    if (directory / "packed-evidence.json").exists():
        raise ValueError("证据目录已包含合并索引")
    original = (directory / "commands.json").read_bytes()
    commands = json.loads(original)
    if not commands:
        raise ValueError("命令索引为空")
    output = bytearray()
    sources = {}
    for number, command in enumerate(commands, 1):
        header = (f"=== {number:03d} {command['label']} ===\n"
                  f"argv={json.dumps(command['argv'], ensure_ascii=False)}\n"
                  f"exit_code={command['exit_code']}\n")
        output.extend(header.encode("utf-8"))
        for stream in ("stdout", "stderr"):
            name = command[stream]
            source = (directory / name).resolve()
            if source.parent != directory.resolve() or source.suffix != ".log" or source.is_symlink():
                raise ValueError("原始日志必须是当前目录中的普通日志文件")
            data = source.read_bytes()
            sources[source] = data
            output.extend(f"[{stream}]\n".encode())
            command[stream] = "commands.log"
            command[stream + "_range"] = {
                "offset": len(output), "length": len(data), "sha256": digest(data), "original_file": name,
            }
            output.extend(data)
            output.extend(b"\n" if data else b"(empty)\n")
        output.extend(b"\n")
    if set(directory.glob("*.log")) != set(sources):
        raise ValueError("存在未被命令索引引用的日志")
    auxiliary = {}
    for pattern in ("*.exit", "*.mtime"):
        for source in directory.glob(pattern):
            if source.is_symlink():
                raise ValueError("辅助证据不能是符号链接")
            data = source.read_bytes()
            sources[source] = data
            auxiliary[source.name] = {"text": data.decode("utf-8"), "sha256": digest(data)}
    manifest = {
        "format": "command-stream-byte-ranges-v1", "prepared_by": operator,
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "original_commands_sha256": digest(original), "commands_log_sha256": digest(output),
        "stream_count": len(commands) * 2, "auxiliary_files": auxiliary,
    }
    return commands, bytes(output), manifest, sources


def pack(directory, operator):
    if not directory.is_relative_to(ROOT / "evidence/e3") or not (directory / "run.json").is_file():
        raise ValueError("请选择仓库 evidence/e3 下的具体运行目录")
    run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    if run.get("status") not in ("PASSED", "FAILED"):
        raise ValueError("运行尚未结束，不能整理证据")
    groups = [(path.parent, prepare_group(path.parent, operator))
              for path in sorted(directory.rglob("commands.json"))]
    if not groups:
        raise ValueError("未找到命令索引")
    archive = ROOT / "work/e3/evidence-originals" / run["run_id"]
    if not archive.resolve().is_relative_to(ROOT / "work/e3") or archive.exists():
        raise ValueError("原始证据存放路径无效或已存在")
    shutil.copytree(directory, archive)
    # 先验证原始副本和所有输出，再调整索引与文件布局。
    for group, (_, _, _, sources) in groups:
        for source, data in sources.items():
            if (archive / source.relative_to(directory)).read_bytes() != data:
                raise ValueError("原始证据副本不完整")
    count = 0
    for group, (commands, output, manifest, sources) in groups:
        if any(source.read_bytes() != data for source, data in sources.items()):
            raise ValueError("整理期间原始证据发生变化")
        (group / "commands.log").write_bytes(output)
        write_json(group / "commands.json", commands)
        write_json(group / "packed-evidence.json", manifest)
        for command in commands:
            for stream in ("stdout", "stderr"):
                source = group / command[stream + "_range"]["original_file"]
                if read_stream(group, command, stream) != sources[source]:
                    raise ValueError("合并日志与原始输出不一致")
        for source in sources:
            source.unlink()
        count += len(sources)
    print(f"STATUS=PACKED\nEVIDENCE_DIR={directory}\nARCHIVE_DIR={archive}\nCONSOLIDATED_FILES={count}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--operator", help="整理证据的操作者")
    parser.add_argument("--read", metavar="LABEL", help="读取指定命令的原始输出")
    parser.add_argument("--stream", choices=("stdout", "stderr"), default="stdout")
    args = parser.parse_args()
    directory = args.directory.resolve()
    try:
        if args.read:
            commands = json.loads((directory / "commands.json").read_text(encoding="utf-8"))
            matches = [item for item in commands if item["label"] == args.read]
            if len(matches) != 1:
                raise ValueError("命令标签不存在或不唯一")
            sys.stdout.buffer.write(read_stream(directory, matches[0], args.stream))
        else:
            if not args.operator or not args.operator.strip():
                parser.error("整理证据必须提供 --operator")
            pack(directory, args.operator)
    except (OSError, ValueError, KeyError) as exc:
        print("证据处理失败：" + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
