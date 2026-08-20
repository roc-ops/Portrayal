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
# no-cache static server: stock http.server lets browsers serve a stale build
install -m 755 tools/serve.py "$STAGE/serve.py"
cat > "$STAGE/index.html" <<'HTML'
<!doctype html><meta charset="utf-8"><title>NDV</title>
<meta http-equiv="refresh" content="0; url=demo/">
<p>Redirecting to <a href="demo/">the NDV demo</a>.</p>
HTML

# COPYFILE_DISABLE stops macOS tar emitting ._ AppleDouble files for xattrs
COPYFILE_DISABLE=1 tar czf - -C "$STAGE" . \
  | ssh "$TARGET" "rm -rf ${REMOTE:?}/* && tar xzf - -C '$REMOTE' && find '$REMOTE' -name '._*' -delete"
ssh "$TARGET" "bash -s" <<'REMOTE'
set -e
systemctl is-active ndv-demo >/dev/null 2>&1 && sudo systemctl restart ndv-demo
# the server needs a moment to rebind after a restart - poll rather than
# curl once and report a spurious 000
for i in $(seq 1 20); do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9003/demo/ || true)
  [ "$code" = "200" ] && { echo "demo: HTTP 200 (ready after ${i} tr(y|ies))"; exit 0; }
  sleep 0.5
done
echo "demo: NOT READY (last code ${code:-none})" >&2
exit 1
REMOTE
