#!/bin/bash
# Copy TheStage CLI skills into a project so every coding agent finds them.
#
#     install_skills.sh <project root> [skill ...]     # default: all skills
#
# Layout written (one real copy, no duplication):
#   .agents/skills/<name>/       the files: the cross-agent Agent Skills location
#                                (OpenAI Codex, Gemini CLI, GitHub Copilot, Cursor, ...)
#   .claude/skills/<name>        symlink -> ../../.agents/skills/<name>
#                                (Claude Code / Agent SDK; Cursor and Grok also read it)
#   AGENTS.md                    a marked index of every installed thestage-* skill, for agents
#                                that read instructions but not skills; replaced on re-install
# Re-running updates in place. Nothing is committed: review and commit the result.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/skills"
DST="${1:?usage: install_skills.sh <project root> [skill ...]}"; shift
[ -d "$DST" ] || { echo "no such directory: $DST" >&2; exit 1; }
SKILLS=()
for s in "$@"; do SKILLS+=("${s%/}"); done              # tab completion adds a trailing slash
[ ${#SKILLS[@]} -gt 0 ] || SKILLS=($(ls "$SRC"))
for core in thestage-cli thestage-troubleshooting; do    # every other skill routes through these
    [[ " ${SKILLS[*]} " == *" $core "* ]] || SKILLS+=("$core")
done
for s in "${SKILLS[@]}"; do                              # validate everything before writing
    [ -f "$SRC/$s/SKILL.md" ] || { echo "unknown skill: $s (have: $(ls "$SRC" | tr '\n' ' '))" >&2; exit 1; }
done

mkdir -p "$DST/.agents/skills" "$DST/.claude/skills"
for s in "${SKILLS[@]}"; do
    rsync -a --delete --exclude '__pycache__' "$SRC/$s/" "$DST/.agents/skills/$s/"
    link="$DST/.claude/skills/$s"
    if [ -L "$link" ]; then
        rm "$link"
    elif [ -e "$link" ]; then                             # never delete a real folder
        echo "skip link: $link exists and is not a symlink (a vendored copy?)" >&2
        continue
    fi
    ln -s "../../.agents/skills/$s" "$link"
done

# index of every thestage-* skill now in the project (a subset install keeps earlier ones)
begin="<!-- thestage-skills:begin -->"; end="<!-- thestage-skills:end -->"
block="$begin
## TheStage platform skills

Skills for the TheStage AI platform (\`thestage\` CLI) live in \`.agents/skills/\`
(also linked from \`.claude/skills/\`). Before running \`thestage\` commands, read the
matching \`SKILL.md\` and follow it; start with \`thestage-cli\`.
"
for f in "$DST"/.agents/skills/thestage-*/SKILL.md; do
    s=$(basename "$(dirname "$f")")
    d=$(sed -n 's/^description: //p' "$f" | head -1)
    block+="
- [\`$s\`](.agents/skills/$s/SKILL.md): $d"
done
block+="
$end"
A="$DST/AGENTS.md"
if [ -f "$A" ] && grep -qF "$begin" "$A"; then
    grep -qF "$end" "$A" || { echo "$A has '$begin' but no '$end': fix it by hand" >&2; exit 1; }
    python3 - "$A" "$begin" "$end" "$block" <<'PY'
import re, sys
path, b, e, block = sys.argv[1:]
s = open(path).read()
s = re.sub(re.escape(b) + r".*?" + re.escape(e), lambda _: block, s, flags=re.S)
open(path, "w").write(s)
PY
else
    { [ -f "$A" ] && printf '\n'; printf '%s\n' "$block"; } >> "$A"
fi

if git -C "$DST" rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    for p in .agents/skills/thestage-cli/SKILL.md .claude/skills/thestage-cli AGENTS.md; do
        if git -C "$DST" check-ignore -q "$p"; then
            echo "warning: $p is git-ignored in $DST; other checkouts and containers will not see it" >&2
        fi
    done
fi
echo "installed into $DST: ${SKILLS[*]}"
echo "review and commit: git -C \"$DST\" add .agents .claude AGENTS.md"
