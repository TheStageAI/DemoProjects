# TheStage CLI Skills

Agent skills (open Agent Skills format: Claude Code, Codex, Cursor, Gemini CLI, Copilot, Grok, ...) for operating the
[TheStage AI](https://app.thestage.ai) platform with the `thestage` CLI: monitoring instances
and free GPUs, renting from the hardware marketplace, projects and branches, containers,
tasks and watchers, storage, and troubleshooting. Written against `thestage` 0.7.16 and
checked against the CLI's help and source.

| Skill | Use it for |
|---|---|
| [thestage-cli](skills/thestage-cli/SKILL.md) | Start here: install, login, team profiles, object model, help, SSH keys, non-interactive use |
| [thestage-instances](skills/thestage-instances/SKILL.md) | Rented/self-hosted instances, **free GPUs per instance**, **marketplace offers and prices**, rent/terminate, attach to projects |
| [thestage-projects](skills/thestage-projects/SKILL.md) | Clone/init, moving code in, branches, which commit a task runs, default container |
| [thestage-containers](skills/thestage-containers/SKILL.md) | Create (GPU/CPU/shm/volumes/ports), operate, resize, delete, upload/download |
| [thestage-tasks](skills/thestage-tasks/SKILL.md) | Run tasks, prompts, logs, cancel, watchers, parallel runs, env and secrets |
| [thestage-storage](skills/thestage-storage/SKILL.md) | File systems and regions, mounts, data layout, bringing data in, secrets |
| [thestage-troubleshooting](skills/thestage-troubleshooting/SKILL.md) | Error message → cause → fix |

Helper scripts:

| Script | What it does |
|---|---|
| [`gpu_capacity.py`](skills/thestage-instances/scripts/gpu_capacity.py) | Total / reserved / busy / free GPUs on every online instance, per-GPU detail, flags hosts with unlimited containers |
| [`offers.sh`](skills/thestage-instances/scripts/offers.sh) | Marketplace offers (provider, region, CPU, RAM, disk, $/h) without renting |
| [`ts.sh`](skills/thestage-tasks/scripts/ts.sh) | Prompt-free task run / status / logs / wait / watch / ls / cancel |

## Adding the skills to a project

The skills use the open **Agent Skills** format (`<name>/SKILL.md` with `name` and
`description` frontmatter, plus `scripts/`), which most coding agents read. Agents differ only
in **where** they look, so a project gets one real copy and links:

```
<project root>/
├── .agents/skills/<name>/      the files (SKILL.md, scripts/): shared cross-agent location
├── .claude/skills/<name>  ->   symlink to ../../.agents/skills/<name>
└── AGENTS.md                   index block between <!-- thestage-skills:begin/end --> markers
```

| Agent | Reads | Covered by |
|---|---|---|
| Claude Code, Claude Agent SDK | `.claude/skills/` (symlinked dirs are followed) | symlinks (tested: all 7 skills listed) |
| OpenAI Codex | `.agents/skills/` from cwd up to the repo root ([docs](https://developers.openai.com/codex/skills)) | files |
| Cursor | `.cursor/skills/`, and for compatibility `.claude/skills/` and `.codex/skills/` ([docs](https://cursor.com/docs/context/skills)) | symlinks |
| Gemini CLI, GitHub Copilot and other Agent Skills tools | `.agents/skills/` (per community guides; Copilot may also use `.github/skills/`) | files |
| Grok Build (xAI) | `~/.grok/skills/`, Claude Code skills and plugins, `AGENTS.md` ([docs](https://docs.x.ai/build/features/skills-plugins-marketplaces)) | symlinks + `AGENTS.md` |
| Anything that reads only `AGENTS.md` | `AGENTS.md` | index block linking each `SKILL.md` |

Only Claude Code was tested here. Cursor's CLI needed a login and the others were not
installed: check each one once in a real project (ask it to list the TheStage skills).

### Install

```bash
TheStage_CLI_Skills/install_skills.sh <project root>                         # all skills
TheStage_CLI_Skills/install_skills.sh <project root> thestage-instances      # a subset
git -C <project root> add .agents .claude AGENTS.md && git -C <project root> commit -m "Add TheStage skills"
```

The script is idempotent (re-run to update; `rsync --delete` drops removed files, the
`AGENTS.md` block is replaced in place, the rest of `AGENTS.md` is kept). It always adds
`thestage-cli` and `thestage-troubleshooting`, which the others route through, and warns if
the project's `.gitignore` would hide the files.

If the platform copies files itself instead of calling the script, it must:

* copy each skill **directory unchanged** to `.agents/skills/<name>/`: folder name equal to the
  frontmatter `name`, `SKILL.md` in upper case, `scripts/` kept inside its skill, the
  executable bit kept (`rsync -a` / `cp -a`);
* create `.claude/skills/<name>` as a **relative** symlink `../../.agents/skills/<name>`
  (git stores it as a symlink; on Windows checkouts without symlink support, copy the
  directory instead);
* add the `AGENTS.md` index block (see the script for the exact text);
* commit all of it: untracked files never reach other checkouts or task containers.

The `SKILL.md` files call their scripts by project-root paths
(`.agents/skills/<skill>/scripts/...`), which resolve the same for every agent.

The skills need the CLI where the agent runs: `pip install thestage && thestage login`
(or `thestage config set --access-token <TOKEN>`).

## Quick reference (from the project root)

```bash
python3 .agents/skills/thestage-instances/scripts/gpu_capacity.py --detail   # free GPUs
bash    .agents/skills/thestage-instances/scripts/offers.sh Nebius RTX6000 8 930
thestage project attach-instance -rn <instance>
thestage container create -cn <you>-g0 -rn <instance> -i thestageai/qlip-elastic -gpun 1 -cpun 24 -shm 16g -v /mnt/fs/<fs>:/mount/fs0
git commit -am "..." && git push
thestage project run -nl -sa -cn <you>-g0 -t "<title>" "python3 train.py --run r1"
thestage project task logs <task-id> -n 200
```

Paid or destructive commands (`instance rented create -f`, `terminate`, `restart`, `container delete`,
`project delete`, `project reset`) are never run by these skills without explicit approval.
