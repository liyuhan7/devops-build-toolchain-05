import json, tempfile, unittest
from pathlib import Path
from lab import fixture,scan,patch,commit

class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name)/'sample';fixture(self.p)

    def test_independent_known_edges(self):
        r=scan(self.p)
        self.assertEqual(r['actual']['main.o'],['config.h','main.c'])
        self.assertEqual({(f['type'],f['dependency']) for f in r['findings']},{('MISSING','config.h'),('REDUNDANT','unused.h')})

    def test_unchanged_reuses_both_targets(self):
        r=scan(self.p,scan(self.p));self.assertEqual(r['reused'],['main.o','helper.o']);self.assertEqual(r['refreshed'],[])

    def test_include_added_invalidates_cache(self):
        old=scan(self.p)
        (self.p/'main.c').write_text('#include "extra.h"\n'+(self.p/'main.c').read_text());commit(self.p,'new include')
        r=scan(self.p,old)
        self.assertIn(['MISSING','main.o','extra.h'],r['added']);self.assertEqual(len(r['refreshed']),2)

    def test_patch_preserves_redundant_dependency(self):
        r=scan(self.p);diff,plan=patch(self.p,r)
        self.assertIn('+main.o: main.c unused.h config.h',diff)
        self.assertNotIn('-\tgcc',diff)
        self.assertNotIn('config.h',(self.p/'Makefile').read_text())

    def test_old_report_rejected(self):
        r=scan(self.p);r['commit']='0'*40
        with self.assertRaisesRegex(ValueError,'STALE_REPORT'):patch(self.p,r)

    def test_unsafe_dependency_rejected(self):
        r=scan(self.p);r['findings']=[{'type':'MISSING','target':'main.o','dependency':'../outside.h'}]
        with self.assertRaisesRegex(ValueError,'UNSAFE_PATH'):patch(self.p,r)

    def test_unsupported_configuration_rejected(self):
        (self.p/'Makefile').write_text((self.p/'Makefile').read_text().replace('-O0','-include unknown.h'))
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_FLAGS'):scan(self.p)

class StudentE8B(unittest.TestCase):
    def test_patch_keeps_recipe_bytes(self):
        from lab import run
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'sample'
            fixture(p)
            before=(p/'Makefile').read_bytes()
            diff,plan=patch(p,scan(p))
            candidate=Path(directory)/'candidate.patch'
            candidate.write_text(diff)
            run(['git','apply',str(candidate.resolve())],p)
            after=(p/'Makefile').read_bytes()
            recipes=lambda data:[line for line in data.splitlines() if line.startswith(b'\t')]
            self.assertEqual(recipes(before),recipes(after))
            self.assertIn(b'main.o: main.c unused.h config.h',after)
            self.assertEqual(plan[0]['style'],'direct')

class StudentE9B(unittest.TestCase):
    def test_macro_style_patch_updates_definition(self):
        from lab import run
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'sample'
            fixture(p,'macro')
            diff,plan=patch(p,scan(p))
            candidate=Path(directory)/'candidate.patch'
            candidate.write_text(diff)
            run(['git','apply',str(candidate.resolve())],p)
            text=(p/'Makefile').read_text()
            self.assertIn('DEPS = main.c unused.h config.h',text)
            self.assertIn('main.o: $(DEPS)',text)
            self.assertEqual(plan[0]['style'],'macro')
            self.assertFalse(any(x['type']=='MISSING' for x in scan(p)['findings']))

if __name__=='__main__':unittest.main()
