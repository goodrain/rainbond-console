# -*- coding: utf8 -*-
import unittest


def compare_version(currentversion, expectedversion):
    if currentversion == expectedversion:
        return 0
    versions = [currentversion, expectedversion]
    sort_versions = sorted(versions, key=lambda x: [int(str(y)) if str.isdigit(str(y)) else -1 for y in x.split(".")])
    max_version = sort_versions.pop()
    if max_version == currentversion:
        return 1
    return -1


def get_new_versions(currentversion, *version_lists):
    new_versions = []
    for version in version_lists:
        if compare_version(currentversion, version) == -1:
            new_versions.append(version)
    return new_versions


class TestDivision(unittest.TestCase):
    def test_compare_version(self):
        self.assertEqual(compare_version("1.1.1", "1.0.1"), 1)
        self.assertEqual(compare_version("1.1.10", "1.2.1"), -1)
        self.assertEqual(compare_version("1.1.1", "1.1.1"), 0)
        self.assertEqual(compare_version("1.a.1", "1.0.1"), -1)
        self.assertEqual(compare_version("1.0.1", "1.b.1"), 1)

    def test_get_new_versions(self):
        self.assertEqual(get_new_versions("1.8", "1.1", "2.0", "1.7", "0.19", "3.0", "1.8", "1.8.1"), ['2.0', '3.0', '1.8.1'])


if __name__ == '__main__':
    unittest.main()
