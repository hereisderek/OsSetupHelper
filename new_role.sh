#!/bin/bash
# Scaffold a new role from _role_templates/.
# Usage: ./new_role.sh <apps|cli|settings> <os_key: common|mac|linux|win> <role_name> [--config]
# --config scaffolds into config/content/ instead of content/ — use this to
# add a role that only your config repo knows about, or to override/replace
# a same-named role from content/ (config/content/ takes priority).
set -e

CATEGORY="$1"
OS_KEY="$2"
NAME="$3"
LOCATION="content"
[[ "$4" == "--config" ]] && LOCATION="config/content"

if [[ -z "$CATEGORY" || -z "$OS_KEY" || -z "$NAME" ]]; then
    echo "Usage: $0 <apps|cli|settings> <common|mac|linux|win> <role_name> [--config]"
    exit 1
fi

DEST="$LOCATION/$CATEGORY/$OS_KEY/$NAME"
if [[ -e "$DEST" ]]; then
    echo "Error: $DEST already exists."
    exit 1
fi

mkdir -p "$DEST"
cp -R "_role_templates/common/." "$DEST/"
python3 -c "
from pathlib import Path
p = Path('$DEST/meta/main.yml')
p.write_text(p.read_text().replace('role_name: placeholder', 'role_name: $NAME'))
"

echo "Created $DEST"
echo "Next: fill in $DEST/defaults/main.yml (app_pkg_mac/app_pkg_linux/app_pkg_win, app_name), then add it to config/config.yaml under selections.$CATEGORY.$NAME."
