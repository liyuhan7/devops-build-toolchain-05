"""行为回归测试使用独立源码副本，测试证据不写回仓库。"""

from contextlib import contextmanager, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts/e3"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
LINUX_TOOLS = platform.system() == "Linux" and all(shutil.which(tool) for tool in ("gcc", "make", "git", "bash", "timeout"))
REAL_RUN = subprocess.run


@contextmanager
def sandbox():
    with tempfile.TemporaryDirectory(prefix="baseline-regression-") as directory:
        root = Path(directory)
        for relative in ("fixtures/e3", "scripts/e3"):
            shutil.copytree(ROOT / relative, root / relative, ignore=shutil.ignore_patterns("__pycache__"))
        for path in root.rglob("*"):
            if path.is_file() and b"\0" not in path.read_bytes():
                path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
        yield root


def load_runner(name, root):
    spec = importlib.util.spec_from_file_location("regression_" + name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = root
    for key, relative in (("CASE", "fixtures/e3/mdfixer"), ("UPSTREAM", "fixtures/e3/fzy"),
                          ("C0_PATCH", "fixtures/e3/echecker/c0.patch"),
                          ("C1_PATCH", "fixtures/e3/echecker/c1.patch"),
                          ("C2_PATCH", "fixtures/e3/echecker/c2.patch")):
        if hasattr(module, key):
            setattr(module, key, root / relative)
    return module


def invoke(module):
    with patch.object(sys, "argv", [module.__name__, "--operator", "自动回归测试"]), redirect_stdout(io.StringIO()):
        code = module.main()
    paths = list((module.ROOT / "evidence").rglob("run.json"))
    if len(paths) != 1:
        raise AssertionError(f"应保存一份运行记录，实际为 {paths}")
    out = paths[0].parent
    return code, json.loads(paths[0].read_text()), json.loads((out / "commands.json").read_text()), out


def command(argv, cwd, **kwargs):
    return REAL_RUN(argv, cwd=cwd, capture_output=True, text=True, check=True, timeout=60, **kwargs).stdout
