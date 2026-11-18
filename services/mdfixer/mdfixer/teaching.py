"""B 组 MDFixer 的显式 Make 教学补丁与隔离验证。"""
import difflib, json, re, shutil, subprocess, time
from pathlib import Path


def save(p, data):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def run(cmd, cwd):
    p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=30)
    if p.returncode: raise ValueError('COMMAND_FAILED '+repr(cmd)+'\n'+p.stdout+p.stderr)
    return p.stdout


def commit(p, msg):
    run(['git','add','.'],p); run(['git','commit','-m',msg],p)
    return run(['git','rev-parse','HEAD'],p).strip()


def patch(p,report):
    if report['commit']!=run(['git','rev-parse','HEAD'],p).strip(): raise ValueError('STALE_REPORT')
    original=(p/'Makefile').read_text(); changed=original; edits=[]
    for f in report['findings']:
        if f['type']!='MISSING': continue
        t,d=f['target'],f['dependency']
        if not re.fullmatch(r'[\w./-]+',d) or '..' in Path(d).parts or Path(d).is_absolute(): raise ValueError('UNSAFE_PATH')
        if not (p/d).is_file(): raise ValueError('MISSING_INPUT')
        m=re.search(r'^'+re.escape(t)+r': (.*)$',changed,re.M)
        if not m: raise ValueError('UNSUPPORTED_TARGET')
        raw=m[1]; macros=re.findall(r'\$\((\w+)\)',raw)
        if raw.strip()==('$(%s)'%macros[0] if macros else ''):
            name=macros[0]; vm=re.search(r'^'+name+r' = (.*)$',changed,re.M)
            if not vm: raise ValueError('UNSUPPORTED_MACRO')
            changed=changed[:vm.end()]+ ' '+d+changed[vm.end():]; style='macro'
        else:
            changed=changed[:m.end()]+' '+d+changed[m.end():]; style='mixed' if macros else 'direct'
        edits.append({'target':t,'dependency':d,'style':style})
    diff=''.join(difflib.unified_diff(original.splitlines(True),changed.splitlines(True),fromfile='a/Makefile',tofile='b/Makefile'))
    return diff,edits


def validate(p, patchfile, evidence, recheck, fail_test=False):
    evidence.mkdir(parents=True); before=(p/'Makefile').read_bytes()
    sandbox=evidence/'sandbox'; shutil.copytree(p,sandbox,ignore=shutil.ignore_patterns('.git','*.o','app'))
    run(['git','init','-b','main'],sandbox)
    run(['git','config','user.name','ValidationSandbox'],sandbox)
    run(['git','config','user.email','fixture@localhost'],sandbox)
    commit(sandbox,'sandbox input')
    checks={}; error=None
    try:
        run(['git','apply','--check',str(patchfile.resolve())],sandbox); checks['patch_applies']=True
        run(['git','apply',str(patchfile.resolve())],sandbox)
        log=run(['make','clean'],sandbox)+run(['make','app'],sandbox);(evidence/'build.log').write_text(log);checks['build']=True
        output=run(['./app'],sandbox).strip(); checks['test']=output==('99' if fail_test else '1')
        # 变更头文件后执行真实构建，验证原先漏声明造成的增量失败已消除。
        time.sleep(1.05); (sandbox/'config.h').write_text('#define VALUE 2\n')
        (evidence/'incremental.log').write_text(run(['make','app'],sandbox))
        checks['header_change']=run(['./app'],sandbox).strip()=='2'
        recheck_report=recheck(sandbox); save(evidence/'recheck.json',recheck_report)
        checks['no_missing']=not any(f['type']=='MISSING' for f in recheck_report['findings'])
    except (ValueError,subprocess.TimeoutExpired) as ex: error=str(ex)
    accepted=bool(checks) and all(checks.values()) and error is None
    # 全部检查通过前保持输入不变，并保留验证副本作为证据。
    if accepted: (p/'Makefile').write_bytes((sandbox/'Makefile').read_bytes())
    unchanged=(p/'Makefile').read_bytes()==before
    result={'accepted':accepted,'checks':checks,'error':error,'source_unchanged':unchanged,'rollback':not accepted and unchanged}
    save(evidence/'validation.json',result);return result
