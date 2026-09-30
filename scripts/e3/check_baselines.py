"""检查已交付 C0 材料；不将材料完整性等同于实际构建通过。"""

import json
from pathlib import Path
import re
import sys

from run_c0 import source_digest


ROOT = Path(__file__).resolve().parents[2]


def main():
    projects = json.loads((ROOT / "fixtures/e3/projects.json").read_text(encoding="utf-8"))
    fzy = projects["fzy"]
    assert re.fullmatch(r"[0-9a-f]{40}", fzy["upstream_commit"]), "上游 SHA 无效"
    assert re.fullmatch(r"[0-9a-f]{64}", fzy["archive_sha256"]), "归档摘要无效"
    upstream = ROOT / fzy["source_path"]
    c0 = ROOT / fzy["c0_path"]
    assert source_digest(upstream) == fzy["source_tree_sha256"], "上游源码快照摘要不一致"
    assert source_digest(c0) == fzy["c0_source_tree_sha256"], "C0 源码摘要不一致"
    assert (ROOT / fzy["license_path"]).is_file(), "缺少上游许可证"
    assert (upstream / "deps/theft/LICENSE").is_file(), "缺少第三方许可证"
    assert not any(path.name == ".git" for path in (ROOT / "fixtures/e3").rglob("*")), "禁止嵌套 Git 仓库"
    expected = json.loads((ROOT / "fixtures/e3/echecker/expected.json").read_text(encoding="utf-8"))
    assert expected["provenance"] == "TEAM_ORACLE", "人工答案来源不明确"
    assert expected["configuration_id"] == fzy["configuration_id"], "配置标识不一致"
    assert expected["findings"] == [], "C0 限定范围应无 MD/RD"
    assert set(expected["expected_graph"]["src/options.o"]) == {"src/options.c", "src/options.h", "config.h"}
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
    versions = json.loads((ROOT / "fixtures/e3/echecker/commits.json").read_text(encoding="utf-8"))
    assert versions["upstream_commit"] == fzy["upstream_commit"]
    for name, version in versions["versions"].items():
        sha = version["commit_sha"]
        assert sha is None or re.fullmatch(r"[0-9a-f]{40}", sha), f"{name} SHA 无效"
    for path in ["fixtures/e3/README.md", "fixtures/e3/echecker/README.md",
                 "fixtures/e3/echecker/oracle.md", "docs/adr/0002-e3-baseline-decisions.md"]:
        assert (ROOT / path).is_file(), f"缺少材料：{path}"
    print("PASS: C0 材料、源码边界、配置和人工答案一致。")
    if versions["versions"]["C0"]["commit_sha"] is None:
        print("PENDING: C0 真实 Git SHA 待用户提交后回填；不是已完成版本冻结。")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, OSError, ValueError, KeyError) as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        sys.exit(1)
