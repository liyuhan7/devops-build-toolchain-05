"""验证声明完整的基线不会被误报为依赖错误。"""
from buildchecker.fullcheck import analyze


def test_matching_actual_and_declared_dependencies_have_no_findings(tmp_path):
    traces = tmp_path / "trace"
    traces.mkdir()
    records = {
        "t.10": 'execve("/usr/bin/make", ["make", "app"], []) = 0\nclone(flags=SIGCHLD) = 11\n',
        "t.11": 'execve("/usr/bin/cc", ["cc", "-c", "main.c"], []) = 0\n'
                'openat(AT_FDCWD, "main.c", O_RDONLY) = 3\n'
                'openat(AT_FDCWD, "config.h", O_RDONLY) = 4\n'
                'openat(AT_FDCWD, "main.o", O_WRONLY|O_CREAT, 0666) = 5\n',
    }
    for name, text in records.items():
        (traces / name).write_text(text, encoding="utf-8")
    database = tmp_path / "make-db.txt"
    database.write_text("# Files\nmain.o: main.c config.h\n# files hash-table stats:\n", encoding="utf-8")
    result = analyze(traces, database, "/course/project")
    assert result["observed_targets"] == ["main.o"]
    assert result["findings"] == []
    assert {(edge["target"], edge["dependency"]) for edge in result["actual_graph"]} == {
        ("main.o", "main.c"), ("main.o", "config.h")}
