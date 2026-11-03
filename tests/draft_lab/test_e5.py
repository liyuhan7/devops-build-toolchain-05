"""DRAFT E5 目标故障、提示和候选边界测试。"""
import unittest

from scripts.draft import e5
from scripts.draft.prompts import classify_missing_make, render_prompts
from scripts.draft.record_candidates import extract_candidate, validate_candidate


BASELINE = """FROM example.invalid/python@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
WORKDIR /work
COPY main.c Makefile ./
RUN make
CMD [\"./hello\"]
"""


class E5Tests(unittest.TestCase):
    def test_e5_image_tag_uses_stage_run_id_not_operator_id(self):
        tag = e5.image_tag("a1b2c3d4")
        self.assertEqual(tag, "draft-e5-broken:e5-b-a1b2c3d4")
        self.assertNotIn("123456789", tag)

    def test_target_failure_requires_nonzero_and_make_not_found(self):
        result = classify_missing_make("/bin/sh: 1: make: not found\n", 1)
        self.assertTrue(result["passed"])
        self.assertEqual(result["classification"], "MISSING_MAKE")
        self.assertEqual(result["root_cause_lines"][0]["line"], 1)

    def test_network_or_timeout_failure_is_not_e5_success(self):
        self.assertFalse(classify_missing_make("TLS handshake timeout", 1)["passed"])
        self.assertFalse(classify_missing_make("make: not found", 124)["passed"])
        self.assertFalse(classify_missing_make("make: not found", 0)["passed"])

    def test_context_prompt_adds_readme_and_preserves_real_log(self):
        prompts = render_prompts(BASELINE, "make: not found", "Build with make.")
        self.assertNotIn("Project README context", prompts["prompt-error-driven.txt"])
        self.assertIn("Project README context", prompts["prompt-context-driven.txt"])
        self.assertIn("make: not found", prompts["prompt-context-driven.txt"])
        self.assertIn(BASELINE.strip(), prompts["prompt-error-driven.txt"])

    def test_candidate_requires_one_fenced_dockerfile(self):
        response = "Result:\n```dockerfile\n" + BASELINE + "RUN apt-get install -y build-essential\n```\n"
        candidate = extract_candidate(response)
        self.assertIn("FROM example.invalid", candidate)
        with self.assertRaises(ValueError):
            extract_candidate("no fenced candidate")

    def test_candidate_preserves_baseline_and_installs_toolchain(self):
        candidate = BASELINE.replace("RUN make", "RUN apt-get install -y build-essential\nRUN make")
        validate_candidate(candidate, BASELINE)
        explicit = BASELINE.replace(
            "RUN make", "RUN apt-get install -y --no-install-recommends gcc make libc6-dev\nRUN make"
        )
        validate_candidate(explicit, BASELINE)
        with self.assertRaisesRegex(ValueError, "固定输入"):
            validate_candidate(candidate.replace("WORKDIR /work", "WORKDIR /src"), BASELINE)
        with self.assertRaisesRegex(ValueError, "构建工具链"):
            validate_candidate(BASELINE, BASELINE)
        with self.assertRaisesRegex(ValueError, "RUN make 之前"):
            validate_candidate(BASELINE + "RUN apt-get install -y build-essential\n", BASELINE)


if __name__ == "__main__":
    unittest.main()
