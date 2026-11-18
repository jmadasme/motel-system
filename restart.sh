#!/usr/bin/env bash
# Reinicia el servidor central.
cd "$(dirname "$0")"
"$(dirname "$0")/stop.sh"
sleep 1
exec "$(dirname "$0")/start.sh"
