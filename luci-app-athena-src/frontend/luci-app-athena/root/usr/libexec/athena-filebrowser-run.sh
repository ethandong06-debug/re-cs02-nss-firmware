#!/bin/sh
# One-time bootstrap password is passed only until Quantum confirms HTTP readiness.
# Subsequent restarts omit the environment variable so UI password changes persist.
FB_BIN=/usr/bin/filebrowser
FB_CONFIG=/etc/filebrowser-quantum.yaml
FB_DB=/etc/filebrowser-quantum.sqlite
FB_PASS=/etc/filebrowser.password
FB_MARKER=/etc/filebrowser-quantum.initialized
FB_PORT=8081
LAN_IP="$1"

[ -x "$FB_BIN" ] || exit 1
[ -r "$FB_CONFIG" ] || exit 1
case "$LAN_IP" in
	[0-9]*.[0-9]*.[0-9]*.[0-9]*) ;;
	*) exit 1 ;;
esac

if [ ! -s "$FB_MARKER" ] || [ ! -s "$FB_DB" ]; then
	PASS=$(cat "$FB_PASS" 2>/dev/null)
	case "$PASS" in
		????????????????????????????????????????????????) ;;
		*) exit 1 ;;
	esac
	case "$PASS" in *[!0-9a-f]*) exit 1 ;; esac

	FILEBROWSER_ADMIN_PASSWORD="$PASS" "$FB_BIN" -c "$FB_CONFIG" &
	child=$!
	trap 'kill "$child" 2>/dev/null; wait "$child" 2>/dev/null; exit 0' TERM INT
	i=0
	while [ "$i" -lt 45 ]; do
		kill -0 "$child" 2>/dev/null || { wait "$child"; exit $?; }
		if wget -q -O /dev/null "http://$LAN_IP:$FB_PORT/" 2>/dev/null; then
			( umask 077; : > "$FB_MARKER" )
			chmod 600 "$FB_MARKER" 2>/dev/null
			wait "$child"
			exit $?
		fi
		sleep 1
		i=$((i + 1))
	done
	kill "$child" 2>/dev/null
	wait "$child" 2>/dev/null
	exit 1
fi

exec "$FB_BIN" -c "$FB_CONFIG"
