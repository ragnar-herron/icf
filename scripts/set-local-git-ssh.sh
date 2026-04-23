#!/usr/bin/env bash
# One-time: store OpenSSH options in this repo so `git push` always uses the
# ragnarherron key (run in Git Bash from any dir). Uses your current $HOME.
# Usage:  bash scripts/set-local-git-ssh.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
K="$HOME/.ssh/id_ed25519_ragnarherron"
C="$HOME/.ssh/config"
if [[ ! -f "$K" ]]; then
  echo "Missing $K — run:  bash $ROOT/scripts/setup-github-ragnarh-ssh-git-bash.sh" >&2
  exit 1
fi
cd "$ROOT"
if [[ -f "$C" ]]; then
  cmd="ssh -i $K -F $C -o IdentitiesOnly=yes"
else
  cmd="ssh -i $K -o IdentitiesOnly=yes"
fi
git config --local core.sshCommand "$cmd"
echo "Set (this repo only):"
git config --local --get core.sshCommand
echo "Now: git push -u origin main"
