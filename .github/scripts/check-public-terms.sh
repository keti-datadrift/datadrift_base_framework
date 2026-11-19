#!/usr/bin/env bash
# Fail when tracked files (and, optionally, commit messages) contain
# terms that should not appear in this public repository: internal work
# tags, references to unpublished design documents, names of specific
# field applications, and traces of development tooling.
#
#   .github/scripts/check-public-terms.sh               # tracked files
#   .github/scripts/check-public-terms.sh <rev-range>   # + commit messages in range
#
# Commit messages are checked for tooling traces only: a cleanup commit
# may legitimately name the internal tags it removes.
set -u

# Case-sensitive: internal work tags.
TAGS='\bRound[ -]?[0-9]+\b|\bR-D[0-9]+\b|\bR[0-9]{2}(-[A-Z])?\b'
# Case-insensitive: unpublished docs, application names, tooling traces.
TERMS='_specs/|context_workplace|\.dev-context|drift_tool_analysis|keti[-_]veritas|\bveritas\b|\balpr\b|\bclaude\b|\banthropic\b'
# Case-insensitive, commit messages: development tooling traces.
TOOLING='\bclaude\b|\banthropic\b'

# .gitignore lists tooling paths precisely so they stay out; this script
# lists the patterns themselves.
EXCLUDES=(':!.gitignore' ':!.github/scripts/check-public-terms.sh')

status=0

hits=$( { git grep -nIP  "$TAGS"  -- . "${EXCLUDES[@]}";
          git grep -nIiP "$TERMS" -- . "${EXCLUDES[@]}"; } | sort -u )
if [ -n "$hits" ]; then
  echo "Terms not allowed in this public repository were found in tracked files:"
  echo "$hits"
  status=1
fi

if [ $# -ge 1 ]; then
  msgs=$(git log --format='%h %s' -P -i --grep="$TOOLING" "$1") || exit 2
  if [ -n "$msgs" ]; then
    echo "Terms not allowed in this public repository were found in commit messages ($1):"
    echo "$msgs"
    status=1
  fi
fi

[ $status -eq 0 ] && echo "public-terms check: OK"
exit $status
