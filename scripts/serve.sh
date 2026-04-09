#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v xcrun >/dev/null 2>&1; then
  echo "xcrun not found. Install Xcode Command Line Tools first."
  exit 1
fi

if [ -x "/opt/homebrew/opt/ruby/bin/ruby" ]; then
  export PATH="/opt/homebrew/opt/ruby/bin:$PATH"
fi

export GEM_HOME="$ROOT_DIR/.gem4"
export GEM_PATH="$ROOT_DIR/.gem4"
export PATH="$ROOT_DIR/.gem4/bin:$PATH"
export SDKROOT="$(xcrun --show-sdk-path)"
export CPATH="$SDKROOT/usr/include"
export CPLUS_INCLUDE_PATH="$SDKROOT/usr/include/c++/v1"

if [ ! -f "$ROOT_DIR/Gemfile" ]; then
  cat > "$ROOT_DIR/Gemfile" <<'EOF'
source "https://rubygems.org"

gem "jekyll", "~> 4.3"
gem "webrick", "~> 1.8"
gem "jekyll-theme-cayman", "~> 0.2"
EOF
  echo "Created local Gemfile."
fi

if ! bundle -v >/dev/null 2>&1; then
  gem install bundler -v 2.6.9
fi

bundle _2.6.9_ config set --local path ".bundle/vendor-ruby4" >/dev/null
bundle _2.6.9_ install
python scripts/build_publications.py
bundle _2.6.9_ exec jekyll serve --host 127.0.0.1 --port 4000
