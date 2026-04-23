#!/usr/bin/env bash
# One-time setup for Git Bash: key + config for "git@github.com-ragnarh" (ragnarherron on GitHub).
#
#   bash scripts/setup-github-ragnarh-ssh-git-bash.sh           # no browser, quiet if already working
#   bash scripts/setup-github-ragnarh-ssh-git-bash.sh --open-browser   # also open GitHub (optional)
#
# Stops re-opening the "Add SSH key" page every time: if SSH already works, we exit without
# visiting GitHub. Only when auth fails do we show the .pub and optional --open-browser.

set -euo pipefail

KEY="$HOME/.ssh/id_ed25519_ragnarherron"
PUB="${KEY}.pub"
CFG="$HOME/.ssh/config"
GH_HOST="github.com-ragnarh"
OPEN_BROWSER=0
for a in "$@"; do
  if [[ "$a" == "--open-browser" || "$a" == "-b" ]]; then
    OPEN_BROWSER=1
  elif [[ "$a" == "-h" || "$a" == "--help" ]]; then
    echo "Usage: $0 [--open-browser]   (optional: set ICF_GITHUB_USER=name if you have no origin URL yet)"
    exit 0
  fi
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
origin="$(git -C "$REPO_ROOT" config --get remote.origin.url 2>/dev/null || true)"
# Expected GitHub login from remote (git@host:USER/repo.git) or ICF_GITHUB_USER
EXPECTED_USER="${ICF_GITHUB_USER:-}"
if [[ -z "$EXPECTED_USER" && -n "$origin" ]]; then
  if [[ "$origin" =~ ^git@([^:]+):([^/]+)/ ]]; then
    EXPECTED_USER="${BASH_REMATCH[2]}"
  elif [[ "$origin" =~ ^https://github\.com/([^/]+)/ ]]; then
    EXPECTED_USER="${BASH_REMATCH[1]}"
  fi
fi
[[ -z "$EXPECTED_USER" ]] && EXPECTED_USER="ragnar-herron"

echo "== Git Bash user / home =="
echo "  user=${USER:-${USERNAME:-$(whoami 2>/dev/null || id -un 2>/dev/null || echo unknown)}}  HOME=$HOME"
echo ""

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh" 2>/dev/null || true

if [[ ! -f "$KEY" ]]; then
  echo "No key at $KEY — generating a new one."
  ssh-keygen -t ed25519 -f "$KEY" -C "ragnarherron-GitBash" -N ""
else
  echo "Using existing key: $KEY"
fi

if [[ -f "$CFG" ]] && grep -qF "Host $GH_HOST" "$CFG"; then
  echo "Config already has Host $GH_HOST — not duplicating."
else
  {
    echo ""
    echo "# $GH_HOST — use: git@${GH_HOST}:<your-github-username>/icf.git"
    echo "Host $GH_HOST"
    echo "    HostName github.com"
    echo "    User git"
    echo "    IdentityFile $KEY"
    echo "    IdentitiesOnly yes"
  } >> "$CFG"
  echo "Appended Host $GH_HOST to $CFG"
  chmod 600 "$CFG" 2>/dev/null || true
fi

if command -v ssh-add >/dev/null 2>&1; then
  ssh-add "$KEY" 2>/dev/null || true
fi

# Same as Git should use: explicit key + your config
if [[ -f "$CFG" ]]; then
  out=$(ssh -i "$KEY" -F "$CFG" -o IdentitiesOnly=yes -o BatchMode=yes -T "git@$GH_HOST" 2>&1) || true
else
  out=$(ssh -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes -T "git@$GH_HOST" 2>&1) || true
fi
echo "=== ssh -T git@${GH_HOST} ==="
echo "$out"
echo "============================"

# "successfully authenticated" is true for BOTH accounts; require the main user explicitly.
# "Hi ragnarherron" without "!" can wrongly match "Hi ragnarherron-debug!".
if echo "$out" | grep -qF "Hi ragnarherron-debug!"; then
  echo "" >&2
  echo "WRONG GITHUB USER: this key is registered on ragnarherron-debug, not ragnarherron." >&2
  echo "Pushing to ragnarherron/icf will still be denied. Fix (pick one):" >&2
  echo "  1) Log in as ragnarherron-debug → https://github.com/settings/keys → delete this key." >&2
  echo "  Log in as ragnarherron     → https://github.com/settings/keys → add the same public key." >&2
  echo "  (A key can only exist on one GitHub user; delete on debug first, then add on ragnarherron.)" >&2
  echo "  2) Or: ssh-keygen a NEW key, add only to ragnarherron, set IdentityFile in ~/.ssh/config for Host $GH_HOST" >&2
  exit 1
fi
if echo "$out" | grep -qF "Hi ${EXPECTED_USER}!"; then
  echo ""
  echo "SSH is OK for ${EXPECTED_USER} (matches remote owner) — no need to add a key again."
  echo "  cd $REPO_ROOT"
  echo "  bash scripts/set-local-git-ssh.sh   # one-time, so plain git push uses this key"
  echo "  git push -u origin main"
  exit 0
fi

echo ""
echo "GitHub is not accepting this key for user ${EXPECTED_USER} yet. Public key to add (one line) at:"
echo "  https://github.com/settings/keys  -> New SSH key"
cat "$PUB"
echo ""
if [[ -x "/c/Windows/System32/clip.exe" ]]; then
  cat "$PUB" | /c/Windows/System32/clip.exe && echo "(Also copied to Windows clipboard.)"
fi
if [[ "$OPEN_BROWSER" -eq 1 ]] && command -v cmd.exe >/dev/null 2>&1; then
  echo "Opening browser (you passed --open-browser)..."
  cmd.exe //c start "" "https://github.com/settings/keys"
else
  echo "We did not open a browser. To open the keys page yourself:  https://github.com/settings/keys"
  echo "To have this script open it next time, run:  $0 --open-browser"
fi
echo ""
echo "After saving the key on GitHub, re-run:  $0   (it will detect success and stop nagging you.)"
echo "Fingerprint (compare with the key in GitHub):  ssh-keygen -lf $PUB"
exit 1
