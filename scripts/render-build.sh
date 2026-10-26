#!/usr/bin/env bash
# Render build step: installs the Python dependencies and builds the React app into frontend/dist,
# which FastAPI then serves, so the whole product runs as one web service.
set -euo pipefail

NODE_VERSION=22.22.0 # Vite needs Node 20.19+ or 22.12+

node_is_recent() {
  command -v node >/dev/null 2>&1 && node -e '
    const [major, minor] = process.versions.node.split(".").map(Number)
    process.exit(major > 22 || (major === 22 && minor >= 12) || (major === 20 && minor >= 19) ? 0 : 1)'
}

if ! node_is_recent; then
  echo "Installing Node ${NODE_VERSION}"
  NODE_DIR="$PWD/.render/node"
  mkdir -p "$NODE_DIR"
  curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.gz" | tar -xz -C "$NODE_DIR" --strip-components=1
  export PATH="$NODE_DIR/bin:$PATH"
fi
echo "Using Node $(node --version) and $(python --version)"

pip install -r backend/requirements.txt

cd frontend
npm ci --include=dev --no-audit --no-fund
npm run build
