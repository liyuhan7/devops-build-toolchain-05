"""检查已交付 C0/C1/C2 材料；不将材料完整性等同于实际构建通过。"""

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from run_c0 import source_digest


ROOT = Path(__file__).resolve().parents[2]


def main():
    projects = json.loads((ROOT / "fixtures/e3/projects.json").read_text(encoding="utf-8"))
    fzy = projects["fzy"]
    assert re.fullmatch(r"[0-9a-f]{40}", fzy["upstream_commit"]), "上游 SHA 无效"
    assert re.fullmatch(r"[0-9a-f]{64}", fzy["archive_sha256"]), "归档摘要无效"
    upstream = ROOT / fzy["source_path"]
    project = ROOT / fzy["echecker_project_path"]
    assert source_digest(upstream) == fzy["source_tree_sha256"], "上游源码快照摘要不一致"
    assert source_digest(project) == fzy["current_source_tree_sha256"], "当前实验源码摘要不一致"
    assert (ROOT / fzy["license_path"]).is_file(), "缺少上游许可证"
    assert (upstream / "deps/theft/LICENSE").is_file(), "缺少第三方许可证"
    assert not any(path.name == ".git" for path in (ROOT / "fixtures/e3").rglob("*")), "禁止嵌套 Git 仓库"
    versions = json.loads((ROOT / "fixtures/e3/echecker/commits.json").read_text(encoding="utf-8"))
    assert versions["upstream_commit"] == fzy["upstream_commit"]
    for name, version in versions["versions"].items():
        sha = version["commit_sha"]
        assert sha is None or re.fullmatch(r"[0-9a-f]{40}", sha), f"{name} SHA 无效"
    assert fzy["current_experiment_version"] == "C2", "当前实验版本必须为 C2"
    assert versions["versions"]["C1"]["status"] == "COMMITTED", "C1 必须有真实提交"
    assert versions["versions"]["C2"]["status"] in {"PENDING_COMMIT", "COMMITTED"}, "C2 状态无效"
    assert versions["versions"]["C2"]["source_tree_sha256"] == fzy["current_source_tree_sha256"]

    expected = json.loads((ROOT / "fixtures/e3/echecker/expected.json").read_text(encoding="utf-8"))
    assert expected["provenance"] == "TEAM_ORACLE", "C0 人工答案来源不明确"
    assert expected["configuration_id"] == versions["versions"]["C0"]["configuration_id"], "C0 配置标识不一致"
    assert expected["findings"] == [], "C0 限定范围应无 MD/RD"
    assert set(expected["expected_graph"]["src/options.o"]) == {"src/options.c", "src/options.h", "config.h"}

    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        c0 = temporary / "c0"
        c1 = temporary / "c1"
        c2 = temporary / "c2"
        shutil.copytree(upstream, c0)
        for revision, workspace in [("c0", c0), ("c1", c1), ("c2", c2)]:
            if revision == "c1":
                shutil.copytree(c0, c1)
            elif revision == "c2":
                shutil.copytree(c1, c2)
            patch = ROOT / f"fixtures/e3/echecker/{revision}.patch"
            subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
            result = subprocess.run(
                ["git", "apply", "--check", "--ignore-whitespace", str(patch)], cwd=workspace,
                capture_output=True, text=True,
            )
            assert result.returncode == 0, f"{revision.upper()} Patch 无法应用：{result.stderr}"
            subprocess.run(["git", "apply", "--ignore-whitespace", str(patch)], cwd=workspace, check=True)
            shutil.rmtree(workspace / ".git")

        assert source_digest(c0) == fzy["c0_source_tree_sha256"], "重建的 C0 源码摘要不一致"
        assert source_digest(c1) == versions["versions"]["C1"]["source_tree_sha256"], "重建的 C1 源码摘要不一致"
        assert source_digest(c2) == fzy["current_source_tree_sha256"], "重建的 C2 源码摘要不一致"
        assert source_digest(c2) == source_digest(project), "签入的 C2 与 Patch 重建结果不一致"
        c1_sources = {
            path.relative_to(c1): path.read_bytes().replace(b"\r\n", b"\n")
            for path in c1.rglob("*") if path.is_file() and path.suffix in {".c", ".h"}
        }
        c2_sources = {
            path.relative_to(c2): path.read_bytes().replace(b"\r\n", b"\n")
            for path in c2.rglob("*") if path.is_file() and path.suffix in {".c", ".h"}
        }
        assert c1_sources == c2_sources, "C2 不得修改 C1 的 .c/.h 内容"
        upstream_files = {p.relative_to(upstream) for p in upstream.rglob("*") if p.is_file()}
        c0_files = {p.relative_to(c0) for p in c0.rglob("*") if p.is_file()}
        assert upstream_files == c0_files, "C0 文件集合与上游快照不一致"
        # Git 在 Windows 可能转换行尾，源码对照按 LF 规范化。
        normalize = lambda path: path.read_bytes().replace(b"\r\n", b"\n")
        changed = {str(p) for p in upstream_files if normalize(upstream / p) != normalize(c0 / p)}
        assert changed == {"Makefile"}, "C0 只能改变受控 Makefile"
        makefile = (c0 / "Makefile").read_text(encoding="utf-8")
        assert "src/options.o: src/options.c src/options.h config.h" in makefile
        assert "$(filter-out -MD -MMD -MP,$(CFLAGS))" in makefile
        assert "$(filter-out src/options.d,$(OBJECTS:.o=.d))" in makefile

    c1_expected = json.loads((ROOT / "fixtures/e3/echecker/c1-expected.json").read_text(encoding="utf-8"))
    assert c1_expected["provenance"] == "TEAM_ORACLE", "C1 人工答案来源不明确"
    assert c1_expected["source_commit"] == versions["versions"]["C1"]["commit_sha"]
    assert c1_expected["configuration_id"] == versions["versions"]["C1"]["configuration_id"]
    assert len(c1_expected["findings"]) == 1, "C1 必须只有一条 Finding"
    finding = c1_expected["findings"][0]
    assert finding["category"] == "MISSING"
    assert finding["target"] == "src/options.o"
    assert finding["dependency"]["name"] == "src/e3_c1_marker.h"
    assert set(c1_expected["scope"]["actual_project_inputs"]) - set(c1_expected["scope"]["declared_inputs"]) == {"src/e3_c1_marker.h"}
    assert c1_expected["delta"] == {"introduced": [finding["finding_id"]], "resolved": [], "unchanged": []}
    c2_expected = json.loads((ROOT / "fixtures/e3/echecker/c2-expected.json").read_text(encoding="utf-8"))
    assert c2_expected["provenance"] == "TEAM_ORACLE", "C2 人工答案来源不明确"
    assert c2_expected["source_commit"] == versions["versions"]["C2"]["commit_sha"]
    assert c2_expected["configuration_id"] == fzy["configuration_id"]
    assert c2_expected["command_change"] == {
        "path": "Makefile", "variable": "VERSION", "before": "1.1",
        "after": "1.2-e3", "affected_flag": "-DVERSION",
    }
    assert len(c2_expected["findings"]) == 1, "C2 必须保持 C1 的一条 Finding"
    assert c2_expected["findings"][0]["finding_id"] == finding["finding_id"]
    assert c2_expected["delta"] == {"introduced": [], "resolved": [], "unchanged": [finding["finding_id"]]}
    for path in ["fixtures/e3/README.md", "fixtures/e3/echecker/README.md",
                 "fixtures/e3/echecker/oracle.md", "fixtures/e3/echecker/c1.patch",
                 "fixtures/e3/echecker/c1-expected.json", "scripts/e3/run_c1.py",
                 "fixtures/e3/echecker/c2.patch", "fixtures/e3/echecker/c2-expected.json",
                 "scripts/e3/run_c2.py",
                 "docs/adr/0002-e3-baseline-decisions.md"]:
        assert (ROOT / path).is_file(), f"缺少材料：{path}"
    print("PASS: C0/C1/C2 材料、源码边界、配置和人工答案一致。")
    if versions["versions"]["C2"]["commit_sha"] is None:
        print("PENDING: C2 真实 Git SHA 待用户提交后回填；当前材料不是最终版本冻结。")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, OSError, ValueError, KeyError) as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        sys.exit(1)
