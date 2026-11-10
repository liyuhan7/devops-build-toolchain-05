"""验证声明完整、失败打开、元数据句柄与重复读取的检测结果。"""
import pytest

from buildchecker.fullcheck import analyze


@pytest.mark.parametrize(
    "reader_extra",
    [
        pytest.param("", id="matching-declarations"),
        pytest.param(
            'openat(AT_FDCWD, "missing.h", O_RDONLY) = -1 ENOENT (No such file)\n',
            id="failed-open",
        ),
        pytest.param(
            'openat(AT_FDCWD, "include", O_RDONLY|O_DIRECTORY) = 6\n'
            'openat(AT_FDCWD, "metadata.h", O_RDONLY|O_PATH) = 7\n',
            id="metadata-handles",
        ),
        pytest.param(
            'openat(AT_FDCWD, "main.c", O_RDONLY) = 6\n'
            'openat(AT_FDCWD, "config.h", O_RDONLY) = 7\n',
            id="duplicate-reads",
        ),
    ],
)
def test_matching_actual_and_declared_dependencies_have_no_findings(tmp_path, reader_extra):
    traces = tmp_path / "trace"
    traces.mkdir()
    records = {
        "t.10": 'execve("/usr/bin/make", ["make", "app"], []) = 0\nclone(flags=SIGCHLD) = 11\n',
        "t.11": 'execve("/usr/bin/cc", ["cc", "-c", "main.c"], []) = 0\n'
                'openat(AT_FDCWD, "main.c", O_RDONLY) = 3\n'
                'openat(AT_FDCWD, "config.h", O_RDONLY) = 4\n' + reader_extra +
                'openat(AT_FDCWD, "main.o", O_WRONLY|O_CREAT, 0666) = 5\n',
    }
    for name, text in records.items():
        (traces / name).write_text(text, encoding="utf-8")
    database = tmp_path / "make-db.txt"
    database.write_text("# Files\nmain.o: main.c config.h\n# files hash-table stats:\n", encoding="utf-8")
    result = analyze(traces, database, "/course/project")
    assert result["observed_targets"] == ["main.o"]
    assert result["findings"] == []
    assert len(result["actual_graph"]) == 2
    assert {(edge["target"], edge["dependency"]) for edge in result["actual_graph"]} == {
        ("main.o", "main.c"), ("main.o", "config.h")}
