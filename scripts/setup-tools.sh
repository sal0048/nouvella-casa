#!/usr/bin/env bash
# Restore the agent tooling this repo's skills rely on, in a fresh cloud
# container: cadgen (text-to-cad skills) and agent-browser (web automation).
# Safe to re-run.
set -euo pipefail

pip install -q "cadgen==0.6.6"
npm i -g agent-browser >/dev/null

# agent-browser reuses the preinstalled Chromium instead of downloading one.
CHROME=/opt/pw-browsers/chromium-1194/chrome-linux/chrome
if [ -x "$CHROME" ] && ! grep -q AGENT_BROWSER_EXECUTABLE_PATH ~/.bashrc 2>/dev/null; then
  echo "export AGENT_BROWSER_EXECUTABLE_PATH=$CHROME" >> ~/.bashrc
fi

# Chromium trusts the NSS store, not the system bundle: add the session's
# own proxy CAs (the Anthropic ones in /root/.ccr/ca-bundle.crt) so pages
# load with normal TLS verification.
BUNDLE=/root/.ccr/ca-bundle.crt
if [ -f "$BUNDLE" ]; then
  command -v certutil >/dev/null || apt-get install -y -q libnss3-tools >/dev/null
  mkdir -p ~/.pki/nssdb
  [ -f ~/.pki/nssdb/cert9.db ] || certutil -d sql:"$HOME/.pki/nssdb" -N --empty-password
  tmp=$(mktemp -d)
  awk -v d="$tmp" '/BEGIN CERT/{n++} {print > (d "/c" n ".pem")}' "$BUNDLE"
  for f in "$tmp"/c*.pem; do
    if openssl x509 -noout -subject -in "$f" | grep -q "O = Anthropic"; then
      certutil -d sql:"$HOME/.pki/nssdb" -A -t "C,," -n "ccr-$(basename "$f" .pem)" -i "$f"
    fi
  done
  rm -rf "$tmp"
fi

cadgen --version
agent-browser --version
