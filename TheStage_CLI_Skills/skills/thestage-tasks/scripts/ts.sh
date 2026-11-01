#!/bin/bash
# Prompt-free wrapper around `thestage project run` / `project task` for scripts and agents.
# Run it from inside a cloned TheStage project (or set TS_PROJECT_DIR).
#
#   ts.sh run <container> <title> "<command>"   launch with -nl -sa; prints only the task id
#   ts.sh status <task-id>                       the platform's status label, lower case
#   ts.sh logs <task-id> [n]                     last n log lines (default 60); works after the end
#   ts.sh wait <task-id> [poll_s]                block until the task ends; exit 0 only on success
#   ts.sh watch <task-id> [pattern] [poll_s]     like wait, printing new lines matching pattern
#                                                (default Error|Traceback|step|RESULT)
#   ts.sh ls [n]                                 newest n tasks: id status title
#   ts.sh cancel <task-id>
#
# wait/watch exit 0 on finished/completed, 1 on failed/canceled, 3 when the status cannot be
# read 5 times in a row (task not among the newest 200, network, CLI error).
set -u
cd "${TS_PROJECT_DIR:-.}" || exit 1
TO=$(command -v timeout || command -v gtimeout || true)          # stock macOS has neither
tmo() { if [ -n "$TO" ]; then "$TO" "$@"; else shift; "$@"; fi; }
ls_tasks() { printf '0\n' | tmo 90 thestage project task ls -r "${1:-50}" 2>&1 | grep "║ task-"; }
status() {
    ls_tasks 200 | awk -F'║' -v id="$1" '{gsub(/ /, "", $2)} $2 == id {gsub(/^ +| +$/, "", $4); print tolower($4)}'
}
logs() { tmo 120 thestage project task logs "$1" -n "${2:-60}" 2>&1 | grep -v '^\s*$'; }
follow() {  # task, pattern (empty = silent), poll
    local id=$1 pat=$2 poll=$3 seen="" misses=0 s new
    while :; do
        if [ -n "$pat" ]; then
            new=$(logs "$id" 200 | grep -E "$pat")
            [ -n "$new" ] && comm -13 <(echo "$seen" | sort) <(echo "$new" | sort) | head -20
            seen=$new
        fi
        s=$(status "$id")
        case "$s" in
            finished|completed) echo "== $id $s"; return 0 ;;
            failed|canceled|cancelled) echo "== $id $s" >&2; return 1 ;;
            "") misses=$((misses + 1)); [ $misses -ge 5 ] && { echo "== $id status unreadable" >&2; return 3; } ;;
            *) misses=0 ;;
        esac
        sleep "$poll"
    done
}
case "${1:-}" in
run)
    [ $# -ge 4 ] || { echo "usage: ts.sh run <container> <title> \"<command>\"" >&2; exit 2; }
    out=$(printf 'n\n' | tmo 180 thestage project run -nl -cn "$2" -t "$3" -sa "$4" 2>&1)
    id=$(echo "$out" | sed -n "s/.*Task ID: '\(task-[a-z0-9]*\)'.*/\1/p" | head -1)
    [ -n "$id" ] || { echo "$out" >&2; exit 1; }
    echo "$id" ;;
status) status "$2" ;;
logs) logs "$2" "${3:-60}" ;;
wait) follow "$2" "" "${3:-30}" > /dev/null ;;
watch) follow "$2" "${3:-Error|Traceback|step|RESULT}" "${4:-60}" ;;
ls) ls_tasks "${2:-10}" | awk -F'║' '{for (i = 2; i <= 4; i++) gsub(/^ +| +$/, "", $i); print $2, tolower($4), $3}' ;;
cancel) thestage project task cancel "$2" ;;
*) sed -n 2,17p "$0"; exit 2 ;;
esac
