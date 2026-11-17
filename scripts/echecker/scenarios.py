"""在 work 独立副本中执行 E8、E9，课程外层仓库只读。"""
from pathlib import Path
import shutil
import time

from services.echecker.echecker.core import build_baseline, run, save, scan


ROOT = Path(__file__).resolve().parents[2]


def commit(project, message):
    """提交仅限本次受测样例的内部 Git 历史。"""
    run(["git", "add", "."], project)
    run(["git", "commit", "-m", message], project)
    return run(["git", "rev-parse", "HEAD"], project).strip()


def fixture(project):
    project = Path(project)
    shutil.copytree(ROOT / "fixtures/echecker", project)
    run(["git", "init", "-b", "main"], project)
    run(["git", "config", "user.name", "TeachingFixture"], project)
    run(["git", "config", "user.email", "fixture@localhost"], project)
    commit(project, "C0 baseline")


def demo(stage, output):
    output = Path(output)
    if output.exists():
        raise ValueError("OUTPUT_MUST_BE_NEW")
    output.mkdir(parents=True)
    project = output / "project"
    fixture(project)
    if stage == "e8":
        baseline = build_baseline(project, output / "buildchecker")
        save(output / "baseline.json", baseline)
        incremental = scan(project, baseline)
        assert incremental["actual"] == baseline["actual"]
        assert incremental["findings"] == baseline["findings"]
        assert incremental["reused"] == ["main.o", "helper.o"] and not incremental["refreshed"]
        save(output / "incremental.json", incremental)
        (output / "结论.txt").write_text("main.o 缺 config.h、冗余 unused.h；本仓库 BuildChecker 实采基线；两目标复用。\n", encoding="utf-8")
    elif stage == "e9":
        baseline = scan(project)
        save(output / "baseline.json", baseline)
        (output / "C0-build.log").write_text(run(["make", "app"], project), encoding="utf-8")
        assert run(["./app"], project).strip() == "1"
        time.sleep(1.05)
        source = project / "main.c"
        source.write_text(source.read_text().replace("VALUE+helper()", "VALUE+helper()+0"), encoding="utf-8")
        commit(project, "C1 body change")
        log = run(["make", "app"], project)
        (output / "C1-build.log").write_text(log, encoding="utf-8")
        assert " -c main.c -o main.o" in log and "main.o helper.o -o app" in log
        one = scan(project, baseline)
        assert one["reused"] == ["main.o", "helper.o"] and not one["refreshed"]
        assert one["findings"] == baseline["findings"] and not one["added"] and not one["resolved"]
        save(output / "C1.json", one)
        time.sleep(1.05)
        source.write_text('#include "extra.h"\n' + source.read_text(), encoding="utf-8")
        commit(project, "C2 include change")
        (output / "C2-build.log").write_text(run(["make", "app"], project), encoding="utf-8")
        two = scan(project, one)
        assert set(two["refreshed"]) == {"main.o", "helper.o"}
        assert two["added"] == [["MISSING", "main.o", "extra.h"]]
        save(output / "C2.json", two)
        makefile = project / "Makefile"
        makefile.write_text(makefile.read_text().replace("main.c unused.h", "main.c unused.h config.h extra.h"), encoding="utf-8")
        commit(project, "C3 repair declarations")
        three = scan(project, two)
        assert three["actual"] == two["actual"]
        assert sorted(three["resolved"]) == [["MISSING", "main.o", "config.h"], ["MISSING", "main.o", "extra.h"]]
        assert three["findings"] == [{"type": "REDUNDANT", "target": "main.o", "dependency": "unused.h"}]
        save(output / "C3.json", three)
    else:
        raise ValueError("UNSUPPORTED_STAGE")
    (output / "sample-history.txt").write_text(run(["git", "log", "--reverse", "--format=%H %s"], project), encoding="utf-8")
    run(["git", "bundle", "create", str((output / "sample-history.bundle").resolve()), "--all"], project)
    save(output / "gate.json", {"stage": stage, "track": "A", "passed": True})


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["e8", "e9"])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    demo(args.stage, args.out)
