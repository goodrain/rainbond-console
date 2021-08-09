import unittest
import validation


class MyTestCase(unittest.TestCase):
    def test_validate_name(self):
        tests = {
            "": False,

            "aa": True,
            "11": True,
            "a1": True,
            "1a": True,
            "中文": True,
            "aa中文": True,
            "中文aa": True,
            "11中文": True,
            "中文11": True,

            "aa-": False,
            "-aa": False,
            "11-": False,
            "-11": False,
            "中文-": False,
            "-中文": False,

            "aa_": False,
            "_aa": False,
            "11_": False,
            "_11": False,
            "中文_": False,
            "_中文": False,

            "a-a": True,
            "1_1": True,
            "中-_文": True,
            "aa-中文": True,

            ".a-a": False,
            "1_1.": False,
            ".中-_文": False,
            "aa-中文.": False,
        }
        for name in tests:
            self.assertEqual(validation.validate_name(name), tests[name])


if __name__ == '__main__':
    unittest.main()
