# -*- coding: utf-8 -*-
import os
import re
import unittest


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def read_repo_file(path):
    with open(os.path.join(REPO_ROOT, path), "r") as handle:
        return handle.read()


def requirement_version(package_name):
    pattern = re.compile(r"^{0}==([0-9][^\s#]*)$".format(re.escape(package_name)), re.MULTILINE)
    match = pattern.search(read_repo_file("requirements.txt"))
    if not match:
        raise AssertionError("{0} is not pinned in requirements.txt".format(package_name))
    return match.group(1)


def version_tuple(version):
    return tuple(int(part) for part in version.split("."))


class ConsoleImageDependencyCompatibilityTests(unittest.TestCase):
    # capability_id: console.image.python36-websocket-client
    def test_websocket_client_pin_stays_installable_on_python36_image(self):
        dockerfile = read_repo_file("Dockerfile")
        if "FROM python:3.6-" not in dockerfile:
            self.skipTest("console image no longer uses Python 3.6")

        pinned_version = version_tuple(requirement_version("websocket-client"))

        self.assertLessEqual(
            pinned_version,
            version_tuple("1.3.1"),
            "websocket-client releases newer than 1.3.1 are not selected by pip for Python 3.6",
        )
        self.assertGreaterEqual(
            pinned_version,
            version_tuple("0.32.0"),
            "docker-compose 1.27.4 requires websocket-client >= 0.32.0",
        )
        self.assertLess(
            pinned_version,
            version_tuple("1.0.0"),
            "docker-compose 1.27.4 requires websocket-client < 1",
        )
