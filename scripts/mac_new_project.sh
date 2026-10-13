#!/usr/bin/env bash
# Safe, non-destructive installer of a clean orphan worktree; run on YOUR Mac.
# DOES NOT auto-delete or commit anything.
set -euo pipefail
SOURCE_REPO="${SOURCE_REPO:-$HOME/Documents/ICIT2027}"
TARGET_REPO="${TARGET_REPO:-$HOME/Documents/ICIT2027-mirage}"
DATASET_SOURCE="${DATASET_SOURCE:-$SOURCE_REPO/data/raw/sherlock/v3}"
BRANCH="mirage-ot"

echo "Source repo: $SOURCE_REPO"
echo "Target worktree: $TARGET_REPO"
echo "Dataset: $DATASET_SOURCE"
[[ -d "$SOURCE_REPO/.git" ]] || { echo "Missing source .git; aborting"; exit 1; }
[[ -d "$DATASET_SOURCE" ]] || { echo "Missing original dataset; aborting"; exit 1; }
[[ ! -e "$TARGET_REPO" ]] || { echo "Target already exists; aborting"; exit 1; }
cd "$SOURCE_REPO"
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  echo "Branch $BRANCH already exists; aborting (not overwriting)."
  exit 1
fi
if ! git worktree add -h 2>&1 | grep -q -- '--orphan'; then
  echo "Git lacks worktree --orphan; aborting safely. Ask Cursor to prepare a compatible orphan setup."
  exit 1
fi
git worktree add --orphan -b "$BRANCH" "$TARGET_REPO"
mkdir -p "$TARGET_REPO/data/raw/sherlock"
ln -s "$DATASET_SOURCE" "$TARGET_REPO/data/raw/sherlock/v3"
echo 'Worktree ready. Extract the MIRAGE-OT project ZIP into the worktree root.'
echo 'Never commit the absolute-path symlink; it is ignored by .gitignore.'
