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
# published by CI for that commit. The application image itself is built in
# GitHub Actions.
set -euo pipefail

PROJECT_DIR=/srv/tg-bot-ytdl
IMAGE=ghcr.io/vasilevnstas/tg-bot-ytdl

cd "$PROJECT_DIR"

git fetch --prune origin main
git reset --hard origin/main

# The image tag is derived from the checked-out commit, so the running image
# always matches the compose file. If CI has not published this exact commit
# yet (e.g. a newer merge landed while we were deploying), fall back to
# `latest`; the next deploy will pin the correct tag.
TAG="sha-$(git rev-parse HEAD)"
if ! docker manifest inspect "$IMAGE:$TAG" >/dev/null 2>&1; then
    echo "warning: $TAG is not published yet, falling back to latest" >&2
    TAG=latest
fi

if grep -q '^IMAGE_TAG=' .env; then
    sed -i "s|^IMAGE_TAG=.*|IMAGE_TAG=$TAG|" .env
else
    printf 'IMAGE_TAG=%s\n' "$TAG" >> .env
fi

docker compose pull
docker compose up -d --remove-orphans
docker image prune -f --filter "until=168h"

echo "deployed $IMAGE:$TAG"
