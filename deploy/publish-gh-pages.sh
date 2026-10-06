#!/usr/bin/env bash
# Publish the static site to GitHub Pages on this repo (gh-pages branch).
#
# Builds with BASE=/StockTest/ and force-pushes the built tree as a single
# commit to the gh-pages branch of origin. The site is then served at
# https://siddharthajbiswas.github.io/StockTest/ (Pages: branch gh-pages, /).
#
# Usage:  bash deploy/publish-gh-pages.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE="$(git -C "$ROOT" remote get-url origin)"

BASE=/StockTest/ bash "$ROOT/deploy/build-pages.sh"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cp -R "$ROOT/build/pages/." "$TMP/"
cd "$TMP"
git init -q
git checkout -q -b gh-pages
git add -A
git commit -q -m "Deploy StockTest ($(git -C "$ROOT" rev-parse --short HEAD))"
git push -q -f "$REMOTE" gh-pages
echo "Published. GitHub Pages rebuilds in about a minute:"
echo "  https://siddharthajbiswas.github.io/StockTest/"
