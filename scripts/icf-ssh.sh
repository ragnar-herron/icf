#!/usr/bin/env bash
# ICF repo: force ssh to use the ragnarherron key + config (works around Git/SSH
# on Windows not picking up Host github.com-ragnarh without agent).
# Source from Git Bash:  source scripts/icf-ssh.sh
# Or run:                 bash scripts/push-icf.sh

icf_key="${HOME?}/.ssh/id_ed25519_ragnarherron"
icf_cfg="${HOME}/.ssh/config"

if [[ ! -f "$icf_key" ]]; then
  echo "Missing private key: $icf_key" >&2
  echo "Run:  bash scripts/setup-github-ragnarh-ssh-git-bash.sh" >&2
  if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    return 1
  fi
  exit 1
fi

# Prefer explicit key + your config; IdentitiesOnly avoids wrong key being offered
if [[ -f "$icf_cfg" ]]; then
  export GIT_SSH_COMMAND="ssh -i ${icf_key} -F ${icf_cfg} -o IdentitiesOnly=yes"
else
  export GIT_SSH_COMMAND="ssh -i ${icf_key} -o IdentitiesOnly=yes"
fi
