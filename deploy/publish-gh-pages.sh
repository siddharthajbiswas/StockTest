#!/usr/bin/env bash
# Publish the static site to this repo's two hosting branches.
#
#   gh-pages      built for /StockTest/       -> https://siddharthajbiswas.github.io/StockTest/
#   biswas-pages  built for /sid/stocktest/   -> https://www.biswas.net/sid/stocktest/
#                 (rahulbiswas/rahulbiswas.github.io syncs it into sid/stocktest/
#                  hourly; see .github/workflows/sync-sid.yml there)
#
# Each branch is force-pushed as a single commit of the built tree.
#
# Usage:  bash deploy/publish-gh-pages.sh            # both
#         bash deploy/publish-gh-pages.sh gh-pages   # just one
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE="$(git -C "$ROOT" remote get-url origin)"
SHA="$(git -C "$ROOT" rev-parse --short HEAD)"
TARGETS=("${@:-gh-pages biswas-pages}")
read -r -a TARGETS <<< "${TARGETS[*]}"

publish() {  # branch base
  BASE="$2" bash "$ROOT/deploy/build-pages.sh"
  local tmp; tmp="$(mktemp -d)"
  cp -R "$ROOT/build/pages/." "$tmp/"
  (
    cd "$tmp"
    git init -q
    git checkout -q -b "$1"
    git add -A
    git commit -q -m "Deploy StockTest ($SHA) for $2"
    git push -q -f "$REMOTE" "$1"
  )
  rm -rf "$tmp"
  echo "Published $1 (base $2)."
}

for t in "${TARGETS[@]}"; do
  case "$t" in
    gh-pages)     publish gh-pages /StockTest/ ;;
    biswas-pages) publish biswas-pages /sid/stocktest/ ;;
    *) echo "unknown target $t" >&2; exit 1 ;;
  esac
done
