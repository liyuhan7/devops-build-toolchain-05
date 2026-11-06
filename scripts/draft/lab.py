"""在共享仓库中运行 B 组 DRAFT 教学实验。"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
TRACK = 'B'
SERVICE = 'draft'
IMAGE = 'draft-lab:B05'
SERVICE_TEST_ARGS = ['pytest', '-c', 'services/draft/pytest.ini', 'services/draft/tests']
RECORDED_CANDIDATE = ROOT / 'fixtures/ci-candidates/context-driven.Dockerfile'

def execute(command, folder, timeout=1800):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'command.json').write_text(json.dumps(command, indent=2), encoding='utf-8')
    with (folder / 'stdout.log').open('w', encoding='utf-8') as out, (folder / 'stderr.log').open('w', encoding='utf-8') as err:
        try:
            code = subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=out, stderr=err, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            code = 124
            if '--cidfile' in command:
                cid_file = Path(command[command.index('--cidfile') + 1])
                if cid_file.is_file():
                    cid = cid_file.read_text().strip()
                    if len(cid) == 64 and all(c in '0123456789abcdef' for c in cid):
                        try:
                            subprocess.run(['docker', 'rm', '-f', cid], stdout=err, stderr=err, timeout=20)
                        except (OSError, subprocess.TimeoutExpired):
                            err.write('\nCleanup incomplete; inspect saved service container ID.\n')
    (folder / 'exit-code.json').write_text(json.dumps({'exit_code': code}), encoding='utf-8')
    for name in ('stdout.log', 'stderr.log'):
        lines = (folder / name).read_text(encoding='utf-8', errors='replace').splitlines()
        print('\n'.join(lines[-35:]))
    return code

def container(extra=()):
    return ['docker', 'run', '--rm', '--user', f'{os.getuid()}:{os.getgid()}', '-e', 'HOME=/tmp', *extra]

def main(argv=None):
    parser = argparse.ArgumentParser(description='B 组 DRAFT 教学实验入口')
    parser.add_argument('stage', choices=['doctor', 'build', 'gate', 'e7'])
    parser.add_argument('--out', help='本仓库 work/ 下的新证据目录')
    parser.add_argument('--image', default=IMAGE)
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument('--candidate', help='E7：本人保存的完整 Dockerfile 路径')
    choice.add_argument('--replay', action='store_true', help='E7：使用本仓库 E5/E6 已验证候选')
    parser.add_argument('--build-timeout', type=int, default=600)
    args = parser.parse_args(argv)
    if sys.platform != 'linux':
        parser.error('Run after SSH login on the Linux cloud host; Windows is not the experiment host')
    if args.build_timeout <= 0:
        parser.error('Build timeout must be positive')
    if args.stage in ('gate', 'e7') and not (args.candidate or args.replay):
        parser.error('Specify --candidate PATH or --replay; replay is not fresh model generation')
    if args.stage not in ('gate', 'e7') and (args.candidate or args.replay):
        parser.error('--candidate and --replay are for gate/e7 only')
    output = (ROOT / args.out).resolve() if args.out else ROOT / 'work/draft' / f'B05-{args.stage}-{datetime.now().strftime("%Y%m%d-%H%M%S")}-{uuid.uuid4().hex[:6]}'
    if output != ROOT / 'work' and ROOT / 'work' not in output.parents:
        parser.error('Keep evidence below this repository work/ directory')
    if output == ROOT / 'work' or (output.exists() and any(output.iterdir())):
        parser.error('Use a fresh directory below work/; previous evidence is preserved')
    output.mkdir(parents=True, exist_ok=True)
    meta = {'track': TRACK, 'stage': args.stage, 'time_utc': datetime.now(timezone.utc).isoformat(), 'image': args.image, 'profile': 'single-dockerfile-teaching', 'replay': args.replay}
    (output / 'invocation.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    print(f'EVIDENCE_DIR={output}', flush=True)
    if args.stage == 'doctor':
        return subprocess.run([sys.executable, 'scripts/doctor.py', '--group', 'B', '--out', str(output / 'env.json')], cwd=ROOT).returncode
    if args.stage == 'build':
        code = execute(['docker', 'build', '--load', '--progress=plain', '-f', 'services/draft/Dockerfile', '-t', args.image, '.'], output / 'build', args.build_timeout)
        if code:
            return code
        if execute(['docker', 'image', 'inspect', args.image], output / 'image', 30):
            return 1
        return execute(['docker', 'run', '--rm', '--network', 'none', args.image, *SERVICE_TEST_ARGS], output / 'unit-tests', 180)
    if args.stage in ('gate', 'e7'):
        candidate = (ROOT / args.candidate).resolve() if args.candidate else RECORDED_CANDIDATE
        if not candidate.is_file():
            parser.error(f'Candidate file does not exist: {candidate}')
        candidate_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
        if args.replay:
            provenance = json.loads((candidate.parent / 'provenance.json').read_text(encoding='utf-8'))
            if (provenance.get('candidate_file') != candidate.name
                    or provenance.get('build_dockerfile_sha256') != candidate_hash):
                parser.error('Recorded candidate does not match its E5/E6 provenance record')
            meta['candidate_provenance'] = (candidate.parent / 'provenance.json').relative_to(ROOT).as_posix()
        meta['candidate_sha256'] = candidate_hash
        meta['candidate_source'] = 'caller supplied candidate' if args.candidate else 'recorded E5/E6 verified teaching candidate'
        (output / 'invocation.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        command = [sys.executable, 'scripts/draft/gate.py', '--image', args.image, '--out', str(output / 'gate'),
                   '--candidate', str(candidate), '--build-timeout', str(args.build_timeout)]
        return execute(command, output / 'driver', 12 * args.build_timeout + 1200)

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        raise SystemExit(f'ERROR: {exc}')
