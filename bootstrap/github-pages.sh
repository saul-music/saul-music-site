#!/usr/bin/env bash
# Activa GitHub Pages con fuente "GitHub Actions". Idempotente. Requiere `gh` con acceso al repo.
# Uso: bootstrap/github-pages.sh [owner/repo]   (por defecto el repo del directorio actual)
set -euo pipefail

REPO="${1:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"

if gh api "repos/$REPO/pages" >/dev/null 2>&1; then
  echo "→ Pages ya existe en $REPO; se asegura la fuente 'GitHub Actions'"
  gh api -X PUT "repos/$REPO/pages" -f build_type=workflow
else
  echo "→ activando Pages en $REPO"
  gh api -X POST "repos/$REPO/pages" -f build_type=workflow >/dev/null
fi
gh api "repos/$REPO/pages" --jq '"  url: \(.html_url)  fuente: \(.build_type)"'
