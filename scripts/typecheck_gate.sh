#!/usr/bin/env bash
# Blocking mypy gate for the strict-whitelisted modules.
#
# `make typecheck` runs mypy over the whole tree for an advisory report, but the
# not-yet-annotated modules still emit lax-mode errors (var-annotated, arg-type,
# etc.) that we are not gating on during incremental adoption. This gate fails
# ONLY when a module that has been brought into the strict whitelist regresses.
#
# Keep WHITELIST_RE in sync with the `[mypy-<module>]` strict sections in
# mypy.ini. Today that is: console/repositories/*, console/services/*,
# console/views/*, openapi/*, and www/apiclient/regionapi.py.
set -uo pipefail

WHITELIST_RE='console/repositories/|console/services/|console/views/|openapi/|www/apiclient/regionapi\.py'

OUT=$(mypy --config-file mypy.ini console/ www/ openapi/ 2>&1)
echo "$OUT" | tail -1

HITS=$(echo "$OUT" | grep ': error' | grep -E "$WHITELIST_RE" || true)
if [ -n "$HITS" ]; then
  echo "::error::mypy strict regression in whitelisted modules:"
  echo "$HITS"
  exit 1
fi

echo "typecheck-gate OK: all strict-whitelisted modules are clean"
