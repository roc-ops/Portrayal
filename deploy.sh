#!/usr/bin/env bash
# Build the demo bundle and deploy it to a host running the portrayal-demo service.
#
#   ./deploy.sh user@host [remote-dir]
#
# Ships demo/ + demo2/ + dist/. demo/reference/ is deliberately excluded: it holds
# vendor photos and 3D models that are not ours to redistribute.
#
# BOTH demos ship. demo/ is frozen and stays until v2 is demonstrably better, so
# replacing it would remove the thing we currently show people in order to test
# its replacement. They sit side by side and the landing page offers both.
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
rsync -a --exclude '.DS_Store' library/demo2 "$STAGE/"
rsync -a library/dist "$STAGE/"
# no-cache static server: stock http.server lets browsers serve a stale build
install -m 755 tools/serve.py "$STAGE/serve.py"
# A chooser, not a redirect: with two demos live, silently landing on one of them
# is how you end up testing the wrong one and reporting a bug against the other.
cat > "$STAGE/index.html" <<'HTML'
<!doctype html><meta charset="utf-8"><title>Portrayal</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
 :root{color-scheme:light dark}
 body{font:16px/1.55 system-ui,sans-serif;max-width:34rem;margin:12vh auto;padding:0 1.5rem}
 h1{font-size:1.3rem;margin:0 0 1.5rem}
 a{display:block;padding:.85rem 1rem;margin:.5rem 0;border:1px solid;border-radius:8px;
   text-decoration:none;color:inherit}
 a b{display:block;font-size:1.05rem}
 a span{opacity:.7;font-size:.9rem}
</style>
<h1>Portrayal</h1>
<a href="demo2/"><b>Demo v2</b><span>Explorer with 2D/3D toggle, states, annotate and export</span></a>
<a href="demo/"><b>Demo v1</b><span>The original pages. Frozen.</span></a>
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
  code2=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9003/demo2/ || true)
  # both, because a green light on v1 while v2 404s is the exact failure this
  # deploy exists to catch
  [ "$code" = "200" ] && [ "$code2" = "200" ] && {
    echo "demo: HTTP 200 on /demo/ and /demo2/ (ready after ${i} tr(y|ies))"; exit 0; }
  sleep 0.5
done
echo "demo: NOT READY (/demo/=${code:-none} /demo2/=${code2:-none})" >&2
exit 1
REMOTE
