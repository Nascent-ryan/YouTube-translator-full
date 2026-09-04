#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade --no-cache-dir yt-dlp
python -m pip install --no-cache-dir -e .

provider_version="${BGUTIL_PROVIDER_VERSION:-1.3.2}"
provider_root=".render/bgutil-ytdlp-pot-provider-${provider_version}"

if [[ ! -d "${provider_root}/.git" ]]; then
  mkdir -p .render
  git clone --depth 1 --branch "${provider_version}" \
    https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
    "${provider_root}"
fi

(
  cd "${provider_root}/server"
  npm ci --include=dev
  npx tsc
)

test -f "${provider_root}/server/build/main.js"
