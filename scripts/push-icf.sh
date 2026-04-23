#!/usr/bin/env bash
# Push ICF to GitHub with a forced SSH key (Git Bash on Windows).
# Usage:  cd /c/work/dev/github/icf  &&  bash scripts/push-icf.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1090
source "$(dirname "${BASH_SOURCE[0]}")/icf-ssh.sh" || exit 1
cd "$ROOT"

K="${HOME}/.ssh/id_ed25519_ragnarherron"
C="${HOME}/.ssh/config"

echo "origin=$(git config --get remote.origin.url)"
echo "key=$K"
if [[ -f "$C" ]]; then
  echo "config=$C"
  ssh_cmd=(ssh -i "$K" -F "$C" -o IdentitiesOnly=yes)
else
  echo "config=(none)"
  ssh_cmd=(ssh -i "$K" -o IdentitiesOnly=yes)
fi

out="$("${ssh_cmd[@]}" -o BatchMode=yes -T git@github.com-ragnarh 2>&1)" || true
echo "$out"
if echo "$out" | grep -qF "Hi ragnarherron-debug!"; then
  echo "" >&2
  echo "This key is on ragnarherron-debug, not your main user. See setup script or GitHub → SSH keys." >&2
  exit 1
fi
origin="$(git config --get remote.origin.url)"
exp="${ICF_GITHUB_USER:-}"
if [[ -z "$exp" && -n "$origin" ]]; then
  if [[ "$origin" =~ ^git@([^:]+):([^/]+)/ ]]; then
    exp="${BASH_REMATCH[2]}"
  elif [[ "$origin" =~ ^https://github\.com/([^/]+)/ ]]; then
    exp="${BASH_REMATCH[1]}"
  fi
fi
[[ -z "$exp" ]] && exp="ragnar-herron"
if ! echo "$out" | grep -qF "Hi ${exp}!"; then
  echo "" >&2
  echo "SSH test expected: Hi ${exp}!  (from origin or ICF_GITHUB_USER). Fix:  bash scripts/setup-github-ragnarh-ssh-git-bash.sh" >&2
  echo "  Add key: https://github.com/settings/keys  →  cat $K.pub" >&2
  exit 1
fi

echo "GIT_SSH_COMMAND=$GIT_SSH_COMMAND"
echo ""
export GIT_SSH_COMMAND
git push -u origin main "$@"
