import unittest
from draft.autobuild import prepare_candidate, classify_failure, instructions

BASE = 'FROM python:3.13-slim\nWORKDIR /work\nCOPY main.c Makefile ./\nRUN make\nCMD ["./hello"]\n'
PIN = "FROM python:3.13-slim@sha256:" + "a" * 64
CANDIDATE = BASE.replace("FROM python:3.13-slim", PIN).replace("RUN make", "RUN apt-get update && apt-get install -y build-essential\nRUN make")

class CandidateTests(unittest.TestCase):
    def test_preserves_baseline_and_pin(self):
        self.assertEqual(prepare_candidate(BASE, CANDIDATE), BASE.replace("FROM python:3.13-slim", PIN))

    def test_multiline_install(self):
        candidate = CANDIDATE.replace(" && apt-get", " " + chr(92) + "\n    && apt-get")
        self.assertEqual(prepare_candidate(BASE, candidate), BASE.replace("FROM python:3.13-slim", PIN))

    def test_changed_base_rejected(self):
        with self.assertRaises(ValueError):
            prepare_candidate(BASE, CANDIDATE.replace("python:3.13-slim", "ubuntu:24.04"))

    def test_unpinned_candidate_rejected(self):
        with self.assertRaises(ValueError):
            prepare_candidate(BASE, CANDIDATE.replace(PIN, "FROM python:3.13-slim"))

    def test_bypassed_build_rejected(self):
        with self.assertRaises(ValueError):
            prepare_candidate(BASE, CANDIDATE.replace("RUN make\n", "RUN true\n"))

    def test_replaced_command_rejected(self):
        with self.assertRaises(ValueError):
            prepare_candidate(BASE, CANDIDATE.replace('CMD ["./hello"]', 'CMD ["echo", "hello E3"]'))

    def test_missing_make_is_expected(self):
        self.assertEqual(classify_failure("/bin/sh: 1: make: not found"), "MISSING_MAKE")

    def test_network_failure_is_not_reproduction(self):
        self.assertEqual(classify_failure("failed to resolve source metadata: EOF"), "INFRASTRUCTURE")

    def test_other_failure_is_not_missing_make(self):
        self.assertEqual(classify_failure("cc: error: invalid source"), "OTHER_BUILD_ERROR")

    def test_unfinished_continuation_rejected(self):
        with self.assertRaises(ValueError):
            instructions("RUN apt-get update " + chr(92))

if __name__ == "__main__":
    unittest.main()
