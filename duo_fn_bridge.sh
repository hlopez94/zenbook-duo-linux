#!/bin/bash
set -euo pipefail

# Shell entrypoint for repository consistency.
# The low-level bridge remains in Python because uinput injection is not
# practical to implement robustly in POSIX shell only.

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
CONFIG_FILE=${DUO_FN_BRIDGE_CONFIG:-/etc/default/zenbook-duo-fn-bridge.conf}

MAP_ARGS=()
if [ -f "${CONFIG_FILE}" ]; then
    while IFS= read -r LINE || [ -n "${LINE}" ]; do
        LINE="${LINE%%#*}"
        LINE="${LINE#${LINE%%[![:space:]]*}}"
        LINE="${LINE%${LINE##*[![:space:]]}}"
        [ -z "${LINE}" ] && continue
        if [[ "${LINE}" =~ ^[0-9]+=[A-Z0-9_]+$ ]]; then
            MAP_ARGS+=(--map "${LINE}")
        else
            echo "Ignoring invalid mapping line in ${CONFIG_FILE}: ${LINE}" >&2
        fi
    done < "${CONFIG_FILE}"
fi

if [ -x /usr/local/bin/duo_fn_bridge.py ]; then
    exec /usr/bin/python3 /usr/local/bin/duo_fn_bridge.py "${MAP_ARGS[@]}" "$@"
fi

exec /usr/bin/python3 "${SCRIPT_DIR}/duo_fn_bridge.py" "${MAP_ARGS[@]}" "$@"
