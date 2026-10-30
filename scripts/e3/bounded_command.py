"""限制验证命令的运行时间，并保留超时前的输出。"""

import os
import signal
import subprocess


def run_bounded(argv, *, cwd, stdin=None, timeout=600):
    try:
        process = subprocess.Popen(
            argv, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
            start_new_session=os.name == "posix",
        )
    except OSError as exc:
        return subprocess.CompletedProcess(argv, 125, "", str(exc))
    try:
        stdout, stderr = process.communicate(stdin, timeout=timeout)
        return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)
    except subprocess.TimeoutExpired:
        # make 的编译子进程也必须终止，否则仍会占用资源或持有输出管道。
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        stdout, stderr = process.communicate()
        return subprocess.CompletedProcess(argv, 124, stdout, stderr + f"\n命令超时（{timeout} 秒）\n")
