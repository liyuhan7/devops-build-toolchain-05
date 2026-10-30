"""E4 冒烟测试：确认容器内的 docker 命令能通过挂载的 docker.sock 使用宿主机 Docker。

做法：构建 E3 的 Dockerfile.broken。它应当失败（基础镜像里没有 make），
冒烟测试检查的是“能构建、能拿到完整失败日志和退出码”，而不是构建成功。
这不是 DRAFT 的修复循环；错误定位、提示与候选选择是 E5/E6 的内容。
"""
import subprocess
import time


def run(cmd, timeout=600):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr
    except FileNotFoundError as e:
        return 127, str(e)


def run_smoke(fixture, tag):
    code, server = run(["docker", "version", "--format", "{{.Server.Version}}"], timeout=30)
    if code != 0:
        return {"passed": False, "docker_server": None, "error": server.strip(),
                "hint": "检查 compose.yaml 是否挂载 /var/run/docker.sock，以及 DOCKER_GID 是否正确（make build 会自动设置）"}
    start = time.time()
    code, log = run(["docker", "build", "--progress=plain", "-f", f"{fixture}/Dockerfile.broken", "-t", tag, fixture])
    lines = log.strip().splitlines()
    make_error_line = next((line.strip() for line in lines if "make: not found" in line), None)
    return {
        "fixture": fixture,
        "docker_server": server.strip(),
        "build_exit_code": code,
        "build_seconds": round(time.time() - start, 1),
        "log_tail": lines[-8:],
        "make_error_line": make_error_line,
        "make_not_found": make_error_line is not None,
        "passed": code != 0 and make_error_line is not None,
        "note": "E4 只验证构建链路；E5 须重新保存完整原始构建日志及退出码",
    }
