#!/usr/bin/env bash
# Prepare a private, untracked Dameng Python driver bundle for Docker builds.
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/prepare_dameng_python_driver.sh <dmdbms-root> [output-directory]

Copies the officially supplied dmPython, dmDjango and DPI files from a Dameng
installation into an ignored Docker build context. The destination must not
exist, so an existing private driver bundle is never overwritten.
EOF
}

if [ "$#" -eq 1 ] && [ "$1" = "--help" ]; then
    usage
    exit 0
fi

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    usage >&2
    exit 2
fi

source_root=$1
project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
output_root=${2:-"${project_root}/third_party/dameng"}

required_directories=(
    "${source_root}/drivers/dpi/dependencies"
    "${source_root}/drivers/dpi/include"
    "${source_root}/drivers/python/dmPython"
    "${source_root}/drivers/python/dmDjango/dmDjango3.0"
)

for required_directory in "${required_directories[@]}"; do
    if [ ! -d "${required_directory}" ]; then
        echo "missing required source: ${required_directory}" >&2
        exit 1
    fi
done

runtime_library="${source_root}/drivers/dpi/libdmdpi.so"
if [ ! -f "${runtime_library}" ]; then
    echo "missing required source: ${runtime_library}" >&2
    exit 1
fi

if [ -e "${output_root}" ]; then
    echo "destination already exists: ${output_root}" >&2
    exit 1
fi

output_parent=$(dirname "${output_root}")
mkdir -p "${output_parent}"
staging_root=$(mktemp -d "${output_parent}/.dameng-driver.XXXXXX")
trap 'rm -rf "${staging_root}"' EXIT

mkdir -p "${staging_root}/dpi/dependencies" \
    "${staging_root}/dpi/include" \
    "${staging_root}/drivers/python/dmPython" \
    "${staging_root}/drivers/python/dmDjango/dmDjango3.0"
cp -R "${source_root}/drivers/dpi/dependencies/." "${staging_root}/dpi/dependencies/"
cp -R "${source_root}/drivers/dpi/include/." "${staging_root}/dpi/include/"
cp -R "${source_root}/drivers/python/dmPython/." "${staging_root}/drivers/python/dmPython/"
cp -R "${source_root}/drivers/python/dmDjango/dmDjango3.0/." \
    "${staging_root}/drivers/python/dmDjango/dmDjango3.0/"
cp "${runtime_library}" "${staging_root}/dpi/libdmdpi.so"

mv "${staging_root}" "${output_root}"
trap - EXIT
echo "Dameng Python driver bundle prepared at ${output_root}"
