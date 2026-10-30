#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 VasilevNStas
# SPDX-License-Identifier: MIT
#
# Server-side deploy script, invoked via an SSH key restricted to a forced
# command in ~/.ssh/authorized_keys:
#
#   command="/usr/local/bin/tg-bot-deploy",no-port-forwarding,no-agent-forwarding,no-pty,no-X11-forwarding ssh-ed25519 AAAA...
#
# It updates the compose file from `main` and rolls the container to the image
# published by CI. The application image itself is built in GitHub Actions.
set -euo pipefail

cd /srv/tg-bot-ytdl

git fetch --depth=1 origin main
git reset --hard origin/main

docker compose pull
docker compose up -d --remove-orphans
docker image prune -f --filter "until=168h"
