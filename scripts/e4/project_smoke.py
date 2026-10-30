"""在服务镜像中复跑本组原项目基线，保存实际输出与原始证据。"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=['A', 'B'], required=True)
    parser.add_argument('--operator', required=True)
    parser.add_argument('--repository-sha', required=True)
    args = parser.parse_args()
    if not args.operator.strip() or not re.fullmatch(r'[0-9a-f]{40}', args.repository_sha):
        parser.error('必须提供实际操作者和完整项目 SHA')
    output = ROOT / 'work/e4/project-smoke'
    output.mkdir(parents=True, exist_ok=False)
    versions = json.loads((ROOT / 'fixtures/e3/echecker/commits.json').read_text(encoding='utf-8'))['versions']
    if args.group == 'A':
        cases = [
            ('c0', 'run_c0.py', ['--revision', versions['C0']['commit_sha']]),
            ('c1', 'run_c1.py', []),
            ('c2', 'run_c2.py', []),
            ('md-rd', 'reproduce_a.py', []),
        ]
    else:
        cases = [
            ('draft-functional', 'verify_fzy.sh', ['--revision', args.repository_sha]),
            ('mdfixer', 'verify_repair.py', []),
        ]
    summary = {'provenance': 'ACTUAL_RUN', 'operator': args.operator, 'group': args.group,
               'repository_sha': args.repository_sha, 'cases': [], 'passed': False}
    summary_path = output / 'summary.json'
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for name, script, extra in cases:
        executable = 'bash' if script.endswith('.sh') else sys.executable
        command = [executable, str(ROOT / 'scripts/e3' / script), '--operator', args.operator, *extra]
        print('原项目验证：' + name, flush=True)
        try:
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=240)
            stdout, stderr, code = result.stdout, result.stderr, result.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            stdout, stderr, code = '', str(exc), 125
        (output / f'{name}.stdout.log').write_text(stdout, encoding='utf-8')
        (output / f'{name}.stderr.log').write_text(stderr, encoding='utf-8')
        item = {'case': name, 'argv': command, 'exit_code': code, 'passed': False}
        evidence_match = re.search(r'^EVIDENCE_DIR=(.+)$', stdout, re.MULTILINE)
        if evidence_match:
            evidence = Path(evidence_match.group(1).strip()).resolve()
            if evidence.is_relative_to((ROOT / 'evidence/e3').resolve()) and (evidence / 'run.json').is_file():
                destination = output / 'evidence' / name / evidence.name
                shutil.copytree(evidence, destination)
                run = json.loads((evidence / 'run.json').read_text(encoding='utf-8'))
                item['evidence'] = destination.relative_to(output).as_posix()
                item['status'] = run.get('status')
                item['passed'] = code == 0 and run.get('status') == 'PASSED'
        summary['cases'].append(item)
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(stdout, end='', flush=True)
        if stderr:
            print(stderr, end='', file=sys.stderr, flush=True)
        if not item['passed']:
            print('原项目基线未通过：' + name, flush=True)
            return 1
    # B 组还需在 ECS 宿主机完成 DRAFT 子容器验证，不能提前标为全部通过。
    summary['passed'] = args.group == 'A'
    if args.group == 'B':
        summary['pending_cases'] = ['draft-container']
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'原项目 {args.group} 组容器内基线验证通过。', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
