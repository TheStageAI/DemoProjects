#!/bin/bash
# List hardware-marketplace offers (region, CPU, RAM, disk, $/hour) WITHOUT renting anything.
#
#     offers.sh <provider> <gpu> <num_gpus> <disk_gb>
#     offers.sh Nebius RTX6000 8 930
#     offers.sh Amazon H100 8 1000
#
# `thestage instance rented create` without --force-yes first returns the matching offers and
# then asks "Offer #". stdin is closed here, so the prompt aborts before the rent call.
# Run with a missing value (e.g. no disk size) to see the allowed choices for it.
set -u
[ $# -ge 2 ] || { sed -n 2,10p "$0"; exit 1; }
args=(-n offers-probe-$$ -p "$1" -g "$2")
[ -n "${3:-}" ] && args+=(-ng "$3")
[ -n "${4:-}" ] && args+=(-ds "$4")
# relies on 0.7.16's flow (no rent without an offer id): refuse on other versions until rechecked
v=$(thestage version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
[ "$v" = "0.7.16" ] || { echo "offers.sh was verified on thestage 0.7.16, found '$v': recheck before use" >&2; exit 1; }
TO=$(command -v timeout || command -v gtimeout || true)
${TO:+$TO 60} thestage instance rented create "${args[@]}" < /dev/null 2>&1 \
    | sed 's/[╔╗╚╝╠╣╦╩╬═]//g' | grep -v '^\s*$' | grep -v '^Aborted'
exit 0
