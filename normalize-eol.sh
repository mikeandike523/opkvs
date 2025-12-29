#!/usr/bin/env bash
set -euo pipefail

# Normalize line endings of all non-ignored files in a Git working tree to "\n"

# Ensure we're inside a git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: not inside a Git working tree." >&2
  exit 1
fi

# Get all relevant files:
#   --cached          = tracked files
#   --others          = untracked files
#   --exclude-standard = respect .gitignore, .git/info/exclude, global ignore
git ls-files --cached --others --exclude-standard -z |
while IFS= read -r -d '' path; do
  # Optionally skip directories (git ls-files normally doesn't list them)
  if [ -d "$path" ]; then
    continue
  fi

  # Optional: only act on text-like files (using 'file' if available)
  if command -v file >/dev/null 2>&1; then
    mime_type=$(file --brief --mime-type "$path" || true)
    case "$mime_type" in
      text/*|*xml|*json|*javascript)
        # looks like text/source, proceed
        ;;
      *)
        # Skip non-text files (binaries, images, etc.)
        continue
        ;;
    esac
  fi

  echo "Normalizing line endings in: $path"
  # Replace CRLF (\r\n) and CR (\r) with LF (\n)
  # This effectively normalizes all line endings to "\n".
  perl -pi -e 's/\r\n?/\n/g' "$path"
done

echo "Done normalizing line endings."
