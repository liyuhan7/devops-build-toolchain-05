"""验证目录和仅获取路径句柄的 open 不形成文件读取依赖。"""
import tempfile
import unittest
from pathlib import Path
from buildchecker.fullcheck import execution_graph


class TestMetadataOpens(unittest.TestCase):
    def test_directory_and_path_handles_are_excluded(self):
        with tempfile.TemporaryDirectory() as folder:
            trace = Path(folder)
            (trace / "t.10").write_text('execve("/usr/bin/make", ["make"], []) = 0\nclone(child_stack=NULL, flags=SIGCHLD) = 11\n')
            (trace / "t.11").write_text(
                'execve("/usr/bin/cc", ["cc"], []) = 0\n'
                'openat(AT_FDCWD, "main.c", O_RDONLY) = 3\n'
                'openat(AT_FDCWD, "include", O_RDONLY|O_DIRECTORY) = 4\n'
                'openat(AT_FDCWD, "metadata.h", O_RDONLY|O_PATH) = 5\n'
                'openat(AT_FDCWD, "main.o", O_WRONLY|O_CREAT|O_TRUNC, 0666) = 6\n')
            targets, _ = execution_graph(trace, "/course/project")
            self.assertEqual(set(targets), {"main.o"})
            self.assertEqual(set(targets["main.o"]["dependencies"]), {"main.c"})


if __name__ == "__main__":
    unittest.main()
