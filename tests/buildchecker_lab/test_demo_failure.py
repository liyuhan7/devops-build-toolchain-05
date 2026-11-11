"""E7 合并门禁演示：临时失败用例，演示结束后必须删除。"""
import unittest


class MergeGateDemoFailure(unittest.TestCase):
    def test_intentional_failure(self):
        self.fail("intentional failure for E7 merge gate demonstration")
