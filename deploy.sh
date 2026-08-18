#!/usr/bin/env bash
# Build the demo bundle and deploy it to a host running the ndv-demo service.
#
#   ./deploy.sh user@host [remote-dir]
#
# Ships demo/ + dist/ only. demo/reference/ is deliberately excluded: it holds
# vendor photos and 3D models that are not ours to redistribute.
set -euo pipefail
cd "$(dirname "$0")"
TARGET="${1:?usage: deploy.sh user@host [remote-dir]}"
REMOTE="${2:-/opt/ndv-demo}"

./build.sh
STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
rsync -a --exclude 'reference/' --exclude '.DS_Store' ndv-library/demo "$STAGE/"
rsync -a ndv-library/dist "$STAGE/"
cat > "$STAGE/index.html" <<'HTML'
<!doctype html><meta charset="utf-8"><title>NDV</title>
<meta http-equiv="refresh" content="0; url=demo/">
<p>Redirecting to <a href="demo/">the NDV demo</a>.</p>
HTML

# COPYFILE_DISABLE stops macOS tar emitting ._ AppleDouble files for xattrs
COPYFILE_DISABLE=1 tar czf - -C "$STAGE" . \
  | ssh "$TARGET" "rm -rf ${REMOTE:?}/* && tar xzf - -C '$REMOTE' && find '$REMOTE' -name '._*' -delete"
ssh "$TARGET" "systemctl is-active ndv-demo >/dev/null 2>&1 && sudo systemctl restart ndv-demo; \
               curl -sf -o /dev/null -w 'demo: HTTP %{http_code}\n' http://127.0.0.1:9003/demo/"
