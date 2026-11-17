"""241840198 个人扩展：条件包含配置失效与声明删除。"""
from pathlib import Path
import tempfile

from services.echecker.echecker.core import build_baseline, scan
from scripts.echecker.scenarios import commit, fixture


def test_e8_macro_change_refreshes_conditional_dependency():
    """真实历史图必须在 MODE 打开条件包含后失效。"""
    with tempfile.TemporaryDirectory() as directory:
        project = Path(directory) / 'sample'
        fixture(project)
        header = project / 'config.h'
        header.write_text('#if MODE\n#include "extra.h"\n#endif\n#define VALUE 1\n')
        commit(project, 'conditional include disabled')
        baseline = build_baseline(project, Path(directory) / 'raw')
        assert baseline['actual']['main.o'] == ['config.h', 'main.c']
        makefile = project / 'Makefile'
        makefile.write_text(makefile.read_text().replace('CFLAGS = -O0', 'CFLAGS = -O0 -DMODE=1'))
        commit(project, 'enable conditional include')
        result = scan(project, baseline)
        assert result['key']['flags'] == '-O0 -DMODE=1'
        assert result['actual']['main.o'] == ['config.h', 'extra.h', 'main.c']
        assert result['added'] == [['MISSING', 'main.o', 'extra.h']]
        assert result['reused'] == []
        assert set(result['refreshed']) == {'main.o', 'helper.o'}
        full = scan(project)
        for key in ('actual', 'declared', 'findings'):
            assert result[key] == full[key]


def test_e9_remove_redundant_declaration_reuses_actual_graph():
    """仅删冗余声明应消除 RD，保留 MD 与实际图。"""
    with tempfile.TemporaryDirectory() as directory:
        project = Path(directory) / 'sample'
        fixture(project)
        baseline = scan(project)
        makefile = project / 'Makefile'
        makefile.write_text(makefile.read_text().replace('main.c unused.h', 'main.c'))
        commit(project, 'remove redundant declaration')
        result = scan(project, baseline)
        assert result['actual'] == baseline['actual']
        assert result['reused'] == ['main.o', 'helper.o']
        assert result['refreshed'] == []
        assert result['added'] == []
        assert result['resolved'] == [['REDUNDANT', 'main.o', 'unused.h']]
        assert result['findings'] == [{'type': 'MISSING', 'target': 'main.o', 'dependency': 'config.h'}]
        full = scan(project)
        for key in ('actual', 'declared', 'findings'):
            assert result[key] == full[key]
