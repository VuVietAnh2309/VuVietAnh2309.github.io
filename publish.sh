#!/usr/bin/env bash
# Publish CV changes to the website.
#
#   ./publish.sh                 check the CV builds, then commit + push (site updates in ~2 min)
#   ./publish.sh "message"       same, with your own commit message
#   ./publish.sh --watch         keep running; every time you save a .tex file and stop
#                                editing for 30s, check + commit + push automatically
set -euo pipefail
cd "$(dirname "$0")"

check() {
  # The site build must parse every section, and both PDFs must compile without errors.
  python3 site/build.py --out "${TMPDIR:-/tmp}/cv-site-check" >/dev/null
  for f in resume resume_vi; do
    xelatex -interaction=nonstopmode -halt-on-error "$f.tex" >/dev/null || {
      echo "✗ $f.tex does not compile -- see $f.log. Nothing was pushed."; return 1; }
  done
}

publish() {
  local msg="${1:-Update CV ($(date '+%Y-%m-%d %H:%M'))}"
  if [ -z "$(git status --porcelain)" ]; then echo "No changes to publish."; return 0; fi
  check || return 1
  git add -A
  git commit -q -m "$msg"
  git push -q
  echo "✓ Pushed. The site updates in about 2 minutes: https://$(git remote get-url origin | sed -E 's#.*github.com[:/]([^/]+)/.*#\1#' | tr '[:upper:]' '[:lower:]').github.io"
}

if [ "${1:-}" = "--watch" ]; then
  echo "Watching cv/*.tex and resume*.tex -- Ctrl+C to stop."
  last=""
  while true; do
    sig="$(stat -f '%m %N' resume.tex resume_vi.tex cv/*.tex 2>/dev/null | sort | md5)"
    if [ -n "$last" ] && [ "$sig" != "$last" ]; then
      echo "Change detected, waiting for you to finish editing..."
      while :; do
        sleep 30
        now="$(stat -f '%m %N' resume.tex resume_vi.tex cv/*.tex 2>/dev/null | sort | md5)"
        [ "$now" = "$sig" ] && break
        sig="$now"
      done
      publish || true
    fi
    last="$sig"
    sleep 5
  done
else
  publish "${1:-}"
fi
