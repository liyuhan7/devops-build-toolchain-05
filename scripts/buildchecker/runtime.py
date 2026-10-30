"""保存 A 组命令、日志和退出码，超时时清理本次运行容器。"""
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
SERVICE_TEST_ARGS = ["pytest", "-c", "services/buildchecker/pytest.ini", "services/buildchecker/tests"]


def docker_user_args():
    """Linux 使用宿主 UID；Windows 绑定目录使用镜像的普通用户。"""
    return ["--user", f"{os.getuid()}:{os.getgid()}"] if os.name == "posix" else []


def run_logged(command, folder, timeout=180):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "command.json").write_text(json.dumps(command, indent=2), encoding="utf-8")
    with (folder / "stdout.log").open("w", encoding="utf-8") as out, (folder / "stderr.log").open("w", encoding="utf-8") as err:
        try:
            code = subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=out, stderr=err, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            code = 124
            cid_file = folder / "container-id.txt"
            if cid_file.is_file():
                try:
                    subprocess.run(["docker", "rm", "-f", cid_file.read_text().strip()],
                                   stdout=err, stderr=err, timeout=20)
                except (OSError, subprocess.TimeoutExpired):
                    err.write("\n容器清理未完成，请根据 container-id.txt 核对。\n")
    (folder / "exit-code.json").write_text(json.dumps({"exit_code": code}), encoding="utf-8")
    for name in ("stdout.log", "stderr.log"):
        lines = (folder / name).read_text(encoding="utf-8", errors="replace").splitlines()
        print("\n".join(lines[-35:]), flush=True)
    return code
