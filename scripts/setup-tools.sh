#!/usr/bin/env bash
# Restore the agent tooling this repo's skills rely on, in a fresh cloud
# container: cadgen (text-to-cad skills) and agent-browser (web automation).
# Pass --blender to also build the Blender venv for photoreal renders
# (~370 MB; bpy pins numpy < 2, which would break cadgen, so it lives in
# its own venv at /root/.venvs/blender). Safe to re-run.
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

if [ "${1:-}" = "--blender" ] && [ ! -x /root/.venvs/blender/bin/python ]; then
  python3 -m venv /root/.venvs/blender
  /root/.venvs/blender/bin/pip install -q "bpy==5.0.1" shapely ezdxf
fi

cadgen --version
agent-browser --version
[ -x /root/.venvs/blender/bin/python ] && /root/.venvs/blender/bin/python -c "import bpy; print('blender', bpy.app.version_string)" || true

# Hypit (video production runtime for the .claude/skills/hypit skill).
# Own-organisation use only (Hypit license). Pass --hypit to (re)install.
if [ "${1:-}" = "--hypit" ] || [ "${2:-}" = "--hypit" ]; then
  if [ ! -x /root/tools/hypit/hypit ]; then
    mkdir -p /root/tools
    git clone -q --depth 1 https://github.com/hypit-ai/hypit.git /root/tools/hypit
    (cd /root/tools/hypit && pnpm install --frozen-lockfile)
  fi
  ln -sf /root/tools/hypit/hypit /usr/local/bin/hypit
  hypit --version
fi

# Helper scripts of the cc-blender-skill skills (.claude/skills/*/scripts/*.py)
pip install -q opencv-python-headless scipy 2>/dev/null || true
