from buildchecker.fullcheck import project_path


def test_parent_path_normalizes_within_project():
    assert project_path("../include/./config.h", "/course/project/src", "/course/project") == "include/config.h"
