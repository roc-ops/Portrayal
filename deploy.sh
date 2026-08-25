#!/usr/bin/env bash
# Build the demo bundle and deploy it to a host running the portrayal-demo service.
#
#   ./deploy.sh user@host [remote-dir]
#
# Ships demo/ + dist/ only. demo/reference/ is deliberately excluded: it holds
# vendor photos and 3D models that are not ours to redistribute.
set -euo pipefail
cd "$(dirname "$0")"
TARGET="${1:?usage: deploy.sh user@host [remote-dir]}"
# The demo host still runs the pre-rename service and path. Renaming those is an
# ops task for publication day, not something a build script should do behind
# your back, so the old names stay the default and are overridable.
SERVICE="${PORTRAYAL_SERVICE:-ndv-demo}"
REMOTE="${2:-/opt/$SERVICE}"

./build.sh
STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
rsync -a --exclude 'reference/' --exclude '.DS_Store' library/demo "$STAGE/"
rsync -a library/dist "$STAGE/"
# no-cache static server: stock http.server lets browsers serve a stale build
install -m 755 tools/serve.py "$STAGE/serve.py"
cat > "$STAGE/index.html" <<'HTML'
<!doctype html><meta charset="utf-8"><title>Portrayal</title>
<meta http-equiv="refresh" content="0; url=demo/">
<p>Redirecting to <a href="demo/">the Portrayal demo</a>.</p>
HTML

# COPYFILE_DISABLE stops macOS tar emitting ._ AppleDouble files for xattrs
COPYFILE_DISABLE=1 tar czf - -C "$STAGE" . \
  | ssh "$TARGET" "rm -rf ${REMOTE:?}/* && tar xzf - -C '$REMOTE' && find '$REMOTE' -name '._*' -delete"
# SERVICE has to be handed to the remote shell explicitly: the heredoc below is
# quoted, so every $VAR in it belongs to the far end. It used to be passed
# nowhere at all, which made the guard `systemctl is-active ""` fail, the &&
# short-circuit, and the restart silently never happen. That went unnoticed
# because content is read from disk per request - it only bites when serve.py
# itself changes, and serve.py is what sends the no-cache header that stops a
# browser serving a stale build.
ssh "$TARGET" "SERVICE=$(printf %q "$SERVICE") bash -s" <<'REMOTE'
set -e
: "${SERVICE:?deploy: SERVICE was not passed to the remote shell}"
if systemctl is-active "$SERVICE" >/dev/null 2>&1; then
  # -n so a sudo password prompt fails loudly instead of hanging the deploy
  sudo -n systemctl restart "$SERVICE" && echo "demo: restarted $SERVICE"
else
  echo "demo: $SERVICE is not an active unit - left whatever is running alone" >&2
fi
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
