#!/bin/sh
# Vendors the UI UX Pro Max design data the drafter ranks (Story 12.6): six CSVs and the MIT licence, at a pinned
# commit, with SOURCE.json. Only data is copied; the project's scripts are never copied or run. After a refresh,
# re-run the ranking tests (tests/test_design_direction.py) and review the snapshot changes.
#
#   make design-data                      # the pinned commit below
#   make design-data COMMIT=<sha>         # move the pin on purpose
set -eu
REPO=nextlevelbuilder/ui-ux-pro-max-skill
COMMIT=${1:-28b3b8dee8c976df4fa3e94aed4e092ad43fcb03}
OUT=agent-api/design_data/ui-ux-pro-max
FILES="products ui-reasoning colors typography landing styles"
RAW="https://raw.githubusercontent.com/$REPO/$COMMIT"

mkdir -p "$OUT"
for name in $FILES; do
  curl -fsSL -o "$OUT/$name.csv" "$RAW/src/ui-ux-pro-max/data/$name.csv"
done
curl -fsSL -o "$OUT/LICENSE" "$RAW/LICENSE"
cat > "$OUT/SOURCE.json" <<JSON
{
  "repo": "https://github.com/$REPO",
  "commit": "$COMMIT",
  "path": "src/ui-ux-pro-max/data",
  "files": [$(for name in $FILES; do printf '"%s.csv", ' "$name"; done | sed 's/, $//')],
  "license": "MIT",
  "fetched": "$(date -u +%Y-%m-%d)"
}
JSON
echo "design data at $COMMIT → $OUT"
