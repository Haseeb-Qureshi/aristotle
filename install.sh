#!/usr/bin/env bash
# Install/sync the Aristotle skill to every place an agent might load it.
#
# Why this exists: the skill was hand-copied to four locations over time
# and they drifted. A Hermes runtime then loaded the STALE one — a
# six-day-old procedure with no question ledger — while three current
# copies sat next to it. Skill installs are writable, agents read
# whichever the loader finds first, and nothing reconciles them.
#
#   ./install.sh            sync every target that exists
#   ./install.sh --check    report drift, change nothing (exit 1 if any)
#   ./install.sh --all      create the standard targets even if absent
#   ./install.sh DIR ...    sync to explicit targets
#
# Course directories are NOT skill installs: they get the same files at
# bootstrap and are then owned by the course. Sync one deliberately by
# naming it as an explicit target.

set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# what a self-sufficient install contains
FILES=(SKILL.md bootstrap.md checkpoint.md scheduling.md README.md)
DIRS=(scripts templates references tools)

STANDARD=(
  "$HOME/.agents/skills/aristotle"    # cross-agent convention; Hermes/Codex
  "$HOME/.hermes/skills/aristotle"    # Hermes profile-independent skills
  "$HOME/.claude/skills/aristotle"    # Claude Code
)

mode="sync"; targets=()
for a in "$@"; do
  case "$a" in
    --check) mode="check" ;;
    --all)   mode="all" ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *)       targets+=("$a") ;;
  esac
done

if [ ${#targets[@]} -eq 0 ]; then
  for t in "${STANDARD[@]}"; do
    if [ "$mode" = "all" ] || [ -d "$t" ]; then targets+=("$t"); fi
  done
fi

drift=0
for t in "${targets[@]}"; do
  label="${t/#$HOME/\~}"
  if [ "$mode" = "check" ]; then
    if [ ! -d "$t" ]; then echo "absent   $label"; continue; fi
    diffs=0
    for f in "${FILES[@]}"; do
      [ -f "$SRC/$f" ] || continue
      cmp -s "$SRC/$f" "$t/$f" 2>/dev/null || diffs=$((diffs+1))
    done
    for d in "${DIRS[@]}"; do
      [ -d "$SRC/$d" ] || continue
      diff -rq --exclude=__pycache__ --exclude='*.pyc' \
        "$SRC/$d" "$t/$d" >/dev/null 2>&1 || diffs=$((diffs+1))
    done
    if [ "$diffs" -eq 0 ]; then echo "current  $label"
    else echo "DRIFTED  $label ($diffs paths differ)"; drift=1; fi
    continue
  fi

  mkdir -p "$t"
  for f in "${FILES[@]}"; do [ -f "$SRC/$f" ] && cp "$SRC/$f" "$t/$f"; done
  for d in "${DIRS[@]}"; do
    [ -d "$SRC/$d" ] || continue
    mkdir -p "$t/$d"
    # mirror, but never delete files a host added on purpose
    find "$SRC/$d" -type f ! -name '*.pyc' | while read -r p; do
      rel="${p#$SRC/}"; mkdir -p "$t/$(dirname "$rel")"; cp "$p" "$t/$rel"
    done
  done
  rm -rf "$t/scripts/__pycache__" "$t/tools/__pycache__"
  echo "synced   $label"
done

if [ "$mode" = "check" ] && [ "$drift" -ne 0 ]; then
  echo; echo "Run ./install.sh to reconcile."; exit 1
fi
