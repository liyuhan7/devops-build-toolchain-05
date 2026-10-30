"""保证 JSON Pointer 解析不会误报，真实密钥字面量仍被检出。"""
import unittest

from scripts.secret_scan import scan_text


class SecretScanTests(unittest.TestCase):
    def test_json_pointer_function_is_not_a_secret(self):
        self.assertEqual(scan_text('token = decode_pointer_token(raw_token)', 'code.py'), [])

    def test_quoted_and_unquoted_secret_literals_are_detected(self):
        value = 'a' * 24
        call = 'decode_' + 'pointer_token(raw_token)'
        for line in (f'secret = "{value}"', f'secret={value}', f'secret = "{call}"'):
            with self.subTest(line=line):
                self.assertTrue(scan_text(line, 'config.txt'))

    def test_api_key_signature_is_detected(self):
        key = 'sk-' + 'a' * 24
        self.assertTrue(scan_text(key, 'config.txt'))


if __name__ == '__main__':
    unittest.main()
