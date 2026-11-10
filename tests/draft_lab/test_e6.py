"""E6 输入溯源、构建阶段和镜像验证回归。"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.draft import e6, verify_e6


BASELINE = """FROM example.invalid/python@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
WORKDIR /work
COPY main.c Makefile ./
RUN make
CMD ["./hello"]
"""
CANDIDATE = BASELINE.replace(
    "RUN make", "RUN apt-get update && apt-get install -y build-essential\nRUN make"
)
IMAGE_ID = "sha256:" + "b" * 64


class E6Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.run_dir = self.root / "work/draft/e5/run-01"
        iteration, project, candidates = (self.run_dir / name for name in ("iter-01", "project", "candidates"))
        iteration.mkdir(parents=True)
        project.mkdir()
        candidates.mkdir()
        (iteration / "Dockerfile").write_text(BASELINE, encoding="utf-8")
        (project / "Dockerfile.broken").write_text(BASELINE, encoding="utf-8")
        (project / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
        (project / "Makefile").write_text("all:\n\tcc main.c -o hello\n", encoding="utf-8")
        (project / "README.md").write_text("Build with make.\n", encoding="utf-8")
        candidate_path = candidates / "context-driven.Dockerfile"
        candidate_path.write_text(CANDIDATE, encoding="utf-8")
        candidate_hash = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
        (candidates / "provenance.json").write_text(json.dumps({
            "selected": "context-driven", "selection_reason": "README names the toolchain",
            "validation_status": "PENDING_E6_REAL_BUILD_AND_PROGRAM_VERIFICATION",
            "candidates": {"context-driven": {
                "candidate_file": "candidates/context-driven.Dockerfile",
                "candidate_sha256": candidate_hash,
            }},
        }), encoding="utf-8")
        inputs = {
            path.relative_to(self.run_dir).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(project.iterdir()) if path.is_file()
        }
        (self.run_dir / "input-sha256.json").write_text(json.dumps(inputs), encoding="utf-8")
        (self.run_dir / "invocation.json").write_text(json.dumps({
            "stage": "E5", "track": "B-DRAFT", "source_commit": "a" * 40,
            "operator": {"name": "Test", "student_id": "123456789"},
            "selected_candidate": "context-driven", "candidate_validation": "PENDING_E6",
            "exit_code": 0, "classification": "MISSING_MAKE",
        }), encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def test_loads_selected_candidate_and_checks_its_recorded_hash(self):
        inputs = e6.load_e5_inputs(self.run_dir, root=self.root)
        self.assertEqual(inputs["selection"], "context-driven")
        candidate_path = self.run_dir / "candidates/context-driven.Dockerfile"
        self.assertEqual(inputs["candidate_sha256"], hashlib.sha256(candidate_path.read_bytes()).hexdigest())

    def test_e6_image_tags_use_stage_run_id_not_operator_id(self):
        tags = e6.image_tags("a1b2c3d4e5f6")
        self.assertEqual(tags, (
            "draft-e6-baseline:e6-b-a1b2c3d4e5",
            "draft-e6-candidate:e6-b-a1b2c3d4e5",
        ))
        self.assertNotIn("123456789", " ".join(tags))

    def test_rejects_candidate_hash_mismatch(self):
        path = self.run_dir / "candidates/context-driven.Dockerfile"
        path.write_text(CANDIDATE + "# changed\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            e6.load_e5_inputs(self.run_dir, root=self.root)

    def test_rejects_project_input_hash_mismatch(self):
        (self.run_dir / "project/main.c").write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "输入哈希"):
            e6.load_e5_inputs(self.run_dir, root=self.root)

    def run_scenario(self, verify_output="hello E3\n", initial_stderr="/bin/sh: 1: make: not found\n",
                     candidate_exit_code=0, debian_mirror=None):
        calls = []

        def fake_run(command, folder, timeout, cid_file=None):
            folder = Path(folder)
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "command.json").write_text(json.dumps(command), encoding="utf-8")
            code, stdout, stderr = 0, "", ""
            if command[1] == "build" and "iter-01" in str(command):
                code, stderr = 1, initial_stderr
            elif command[1] == "build":
                code = candidate_exit_code
                stderr = "candidate build failed\n" if code else ""
            elif command[1:3] == ["image", "inspect"]:
                stdout = IMAGE_ID + "\n"
            elif command[1] == "run":
                stdout = verify_output
            for name, content in (("stdout.log", stdout), ("stderr.log", stderr)):
                (folder / name).write_text(content, encoding="utf-8")
            (folder / "exit-code.json").write_text(json.dumps({"exit_code": code}), encoding="utf-8")
            calls.append(command)
            return code

        output = self.root / "work/draft/e6/run-01"
        with patch.object(e6, "run_logged", side_effect=fake_run):
            result = e6.run_e6(self.run_dir, output, debian_mirror=debian_mirror, root=self.root)
        return result, calls, output

    def test_runs_two_builds_then_verifies_built_image_id(self):
        result, calls, output = self.run_scenario()
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(len([c for c in calls if c[1] == "build"]), 2)
        self.assertEqual(result["attempts"][0]["failure_class"], "MISSING_MAKE")
        run_command = next(c for c in calls if c[1] == "run")
        self.assertEqual(run_command[-1], IMAGE_ID)
        self.assertEqual(json.loads((output / "result.json").read_text())["verification"]["actual_output"], "hello E3\n")
        self.assertTrue(verify_e6.verify(output)["passed"])

    def test_mirror_adaptation_preserves_candidate_and_records_derived_dockerfile(self):
        result, _, output = self.run_scenario(debian_mirror="mirrors.aliyun.com")
        source = (output / "iter-02/source-candidate.Dockerfile").read_text(encoding="utf-8")
        built = (output / "iter-02/Dockerfile").read_text(encoding="utf-8")
        self.assertEqual(source, CANDIDATE)
        expected = CANDIDATE.replace(
            "RUN apt-get update",
            "RUN sed -i 's#http://deb.debian.org#https://mirrors.aliyun.com#g' "
            "/etc/apt/sources.list.d/debian.sources \\\n    && apt-get update",
        )
        self.assertEqual(built, expected)
        self.assertEqual(result["candidate_sha256"], hashlib.sha256((output / "iter-02/source-candidate.Dockerfile").read_bytes()).hexdigest())
        self.assertEqual(result["build_adaptation"]["to"], "https://mirrors.aliyun.com")
        self.assertEqual(result["build_dockerfile_sha256"], hashlib.sha256((output / "iter-02/Dockerfile").read_bytes()).hexdigest())
        self.assertTrue(verify_e6.verify(output)["passed"])

    def test_evidence_verifier_rejects_changed_mirror_adaptation(self):
        _, _, output = self.run_scenario(debian_mirror="mirrors.aliyun.com")
        path = output / "iter-02/Dockerfile"
        path.write_text(path.read_text(encoding="utf-8").replace("mirrors.aliyun.com", "evil.example"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "环境适配"):
            verify_e6.verify(output)

    def test_mirror_adaptation_rejects_unsupported_hosts(self):
        with self.assertRaisesRegex(ValueError, "不支持的 Debian 镜像"):
            self.run_scenario(debian_mirror="evil.example")

    def test_evidence_verifier_rejects_changed_program_output(self):
        _, _, output = self.run_scenario()
        (output / "verify/stdout.log").write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "输出"):
            verify_e6.verify(output)

    def test_infrastructure_failure_stops_before_candidate_build(self):
        result, calls, _ = self.run_scenario(initial_stderr="TLS handshake timeout\n")
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(len([c for c in calls if c[1] == "build"]), 1)
        self.assertNotIn("verification", result)

    def test_wrong_program_output_does_not_pass(self):
        result, _, _ = self.run_scenario(verify_output="wrong\n")
        self.assertEqual(result["status"], "FAILED")
        self.assertFalse(result["verification"]["output_matches"])

    def test_candidate_build_failure_stops_before_image_verification(self):
        result, calls, _ = self.run_scenario(candidate_exit_code=23)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["attempts"][1]["build_exit_code"], 23)
        self.assertFalse(any(command[1:3] == ["image", "inspect"] for command in calls))
        self.assertFalse(any(command[1] == "run" for command in calls))


if __name__ == "__main__":
    unittest.main()
