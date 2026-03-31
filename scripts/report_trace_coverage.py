#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


DEFAULT_TEST_LABELS = [
    "console.tests.app_config_group_service_test",
    "console.tests.app_config_test",
    "console.tests.app_import_and_export_service_test",
    "console.tests.app_version_test",
    "console.tests.cnb_build_test",
    "console.tests.config_service_test",
    "console.tests.group_service_test",
    "console.tests.groupapp_backup_listing_test",
    "console.tests.groupapp_backup_migration_test",
    "console.tests.init_cluster_test",
    "console.tests.mcp_query_dependency_ops_test",
    "console.tests.mcp_query_service_test",
    "console.tests.mcp_query_storage_ops_test",
    "console.tests.mcp_query_view_test",
    "console.tests.package_component_service_test",
    "console.tests.regionapi_sse_proxy_test",
    "console.tests.regionapibaseclient_test",
    "console.tests.service_share_test",
    "console.tests.source_component_service_test",
    "console.tests.team_resources_test",
    "console.tests.utils.reqparse_test",
    "console.tests.utils.validation_test",
    "console.tests.utils.cache_test",
    "console.tests.utils.certutil_test",
    "console.tests.utils.version_test",
    "console.tests.utils.timeutil_test",
    "console.tests.utils.urlutil_test",
    "console.tests.utils.randomutil_test",
    "console.tests.utils.image_classify_test",
    "console.tests.utils.oauth_base_test",
    "console.tests.utils.oauth_types_test",
    "console.tests.utils.restful_client_test",
]
SUMMARY_RE = re.compile(r"^\s*(\d+)\s+(\d+)%\s+([A-Za-z0-9_.]+)\s+\(([^)]+)\)$")


def parse_args():
    parser = argparse.ArgumentParser(description="Run trace-based coverage for rainbond-console.")
    parser.add_argument("labels", nargs="*", help="Django test labels to run")
    parser.add_argument(
        "--module-prefix",
        action="append",
        default=["console.", "www."],
        help="Only include modules under this prefix when calculating weighted coverage",
    )
    parser.add_argument("--worst", type=int, default=15, help="How many lowest-coverage modules to print")
    return parser.parse_args()


def main():
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    labels = args.labels or DEFAULT_TEST_LABELS

    env = os.environ.copy()
    pythonpath_parts = [".", "./src/openapi-client"]
    if env.get("PYTHONPATH"):
        pythonpath_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    env.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

    with tempfile.TemporaryDirectory(prefix="console-tracecov-") as coverdir:
        cmd = [
            sys.executable,
            "-m",
            "trace",
            "--count",
            "--missing",
            "--summary",
            "-C",
            coverdir,
            "scripts/run_django_tests.py",
        ] + labels
        proc = subprocess.run(
            cmd,
            cwd=str(repo_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )

    output = proc.stdout
    rows = []
    for line in output.splitlines():
        match = SUMMARY_RE.match(line)
        if not match:
            continue
        line_count = int(match.group(1))
        coverage = int(match.group(2))
        module = match.group(3)
        path = match.group(4)
        if any(module.startswith(prefix) for prefix in args.module_prefix):
            rows.append((line_count, coverage, module, path))

    print("scope: trace sample")
    print("settings: {0}".format(env["DJANGO_SETTINGS_MODULE"]))
    print("labels: {0}".format(", ".join(labels)))

    if not rows:
        print("no matching modules found in trace summary", file=sys.stderr)
        sys.stdout.write(output)
        return 1

    covered = sum(line_count * coverage / 100 for line_count, coverage, _, _ in rows)
    total = sum(line_count for line_count, _, _, _ in rows)
    weighted = round(covered / total * 100, 2) if total else 0.0

    print("matched_modules: {0}".format(len(rows)))
    print("weighted_coverage: {0}%".format(weighted))
    print("lowest_coverage_modules:")
    for line_count, coverage, module, path in sorted(rows, key=lambda item: (item[1], -item[0], item[2]))[: args.worst]:
        print("  {0:>3}%  {1:>5}  {2}  {3}".format(coverage, line_count, module, path))

    if proc.returncode != 0:
        print("\ntrace run failed:\n")
        sys.stdout.write(output)
        return proc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
