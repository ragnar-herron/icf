#!/usr/bin/env bash
# Run from Git Bash: paste key on GitHub, then test SSH and push to ragnarherron/icf.
# Usage: ./scripts/github-ssh-ragnarherron.sh
#    or:  bash scripts/github-ssh-ragnarherron.sh [path-to-private-key-without-.pub]
#
# Requires: the key id_ed25519_ragnarherron(.pub) and ~/.ssh/config Host "github.com-ragnarh"
#   (see earlier setup). Use GitHub user ragnarherron, not ragnarherron-debug.

set -euo pipefail

KEY="${1:-$HOME/.ssh/id_ed25519_ragnarherron}"
PUB="${KEY}.pub"
SSH_HOST="git@github.com-ragnarh"
REPO_SSH="git@github.com-ragnarh:ragnarherron/icf.git"

# Resolve icf repo root (directory containing .git) from script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

clip_copy() {
  if [[ -x "/c/Windows/System32/clip.exe" ]]; then
    /c/Windows/System32/clip.exe
  elif command -v clip.exe >/dev/null 2>&1; then
    clip.exe
  else
    return 1
  fi
}

if [[ ! -f "$PUB" ]]; then
  echo "Missing public key: $PUB" >&2
  echo "Create it first, e.g.:" >&2
  echo "  ssh-keygen -t ed25519 -f \"\$HOME/.ssh/id_ed25519_ragnarherron\" -C ragnarherron-GitHub -N \"\"" >&2
  exit 1
fi

if ! command -v ssh-add >/dev/null 2>&1; then
  echo "ssh-add not found" >&2
  exit 1
fi

# Load private key (ignore if already in agent)
ssh-add "$KEY" 2>/dev/null || true

echo "---- Public key (also copied to Windows clipboard) ----"
cat "$PUB"
echo "----------------------------------------------------"

if cat "$PUB" | clip_copy; then
  echo "OK: public key is on the clipboard (use Ctrl+V in the browser key field)."
else
  echo "Could not use clip.exe; copy the line above manually."
fi

echo ""
echo "Opening: New SSH key (log in as ragnarherron)"
if command -v cmd.exe >/dev/null 2>&1; then
  cmd.exe //c start "" "https://github.com/settings/ssh/new"
else
  echo "  Open: https://github.com/settings/ssh/new"
fi

echo ""
read -r -p "After you click 'Add SSH key' on GitHub, press Enter here to test SSH... " _

echo ""
echo "Running: ssh -T $SSH_HOST"
out="$(ssh -o BatchMode=yes -T "$SSH_HOST" 2>&1 || true)"
echo "$out"

if echo "$out" | grep -qF "Hi ragnarherron-debug!"; then
  echo "" >&2
  echo "This key is on ragnarherron-debug, not ragnarherron — move the key in GitHub or use a new key for ragnarherron." >&2
  exit 1
fi
if ! echo "$out" | grep -qF "Hi ragnarherron!"; then
  echo "" >&2
  echo "SSH auth failed (need Hi ragnarherron!). Check:" >&2
  echo "  - Key added on ragnarherron: https://github.com/settings/keys" >&2
  echo "  - ~/.ssh/config: Host github.com-ragnarh -> correct IdentityFile" >&2
  exit 1
fi

if [[ ! -d "$REPO_ROOT/.git" ]]; then
  echo "Not a git repo: $REPO_ROOT" >&2
  exit 1
fi

cd "$REPO_ROOT"
echo ""
echo "Setting origin to: $REPO_SSH"
git remote set-url origin "$REPO_SSH"
git remote -v
echo ""
echo "Pushing main..."
git push -u origin main
echo "Done."
