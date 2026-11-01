---
name: thestage-cli
description: Start here for any work on the TheStage AI platform with the `thestage` CLI. Covers install, login and tokens, team profiles, the object model (instances, projects, containers, tasks, storage), getting help, debug output, SSH keys, non-interactive use, and which specialised thestage-* skill to load next.
---

# TheStage CLI: setup and orientation

Verified against `thestage` **0.7.16** (`thestage version`). If your version differs, re-check
flags with `--help`; everything below was taken from the CLI's own help and source.

## The object model (read this first)

```
Team (profile) ── Rented instance (GPU host, region)      ── File system (/mnt/fs/<name>, same region)
       │                 │ attached to
       └── Project ──────┤  (git repo hosted by TheStage)
                         └── Container (Docker, N GPUs, M CPUs, volumes) ── Task (one command at one commit)
```

| Object | What it is | Key fact |
|---|---|---|
| **Instance** | A rented (or self-hosted) machine | Must be *attached* to a project before the project can put containers on it |
| **Project** | A git repo on GitHub managed by TheStage, with a deploy key | Tasks run code **from a commit of this repo**, not from your disk |
| **Container** | A Docker container on an instance | Has its own GPUs/CPUs/mounts. **Runs one task at a time (serial queue)** |
| **Task** | `command` + `commit` executed in a container | Fresh checkout per task in `/var/lib/thestage_daemon/tasks/<task-id>/code` |
| **File system** | Network storage mounted on the host at `/mnt/fs/<name>` | Attach only to instances **in the same region**; map into containers with `-v` |

Load the matching skill for the job:

| Job | Skill |
|---|---|
| Monitor rented instances, free GPUs per instance, marketplace offers, rent/terminate, attach to a project | `thestage-instances` |
| Clone/init a project, branches, which commit a task runs | `thestage-projects` |
| Create / start / stop / delete containers, mounts, ports, upload/download files | `thestage-containers` |
| Run tasks, prompts, logs, cancel, watchers, parallel runs | `thestage-tasks` |
| File systems, regions, data layout, secrets | `thestage-storage` |
| Any error message | `thestage-troubleshooting` |

## Install and log in

```bash
pip install thestage            # puts `thestage` on PATH
thestage version
thestage login                  # browser login, creates a profile
# or, headless: token from app.thestage.ai -> Profile -> Access tokens
thestage config set --access-token <TOKEN>
```

`thestage config get` shows the **active profile**, backend URL, config path
(`~/.thestage/config.json`) and the app log directory. It also prints the access token in
clear text: never paste its output into chats, tickets or logs.

### Teams = profiles

Every team you log into becomes a stored profile. All listings (instances, projects,
containers) are **per active profile**.

```bash
thestage config get              # "ACTIVE PROFILE: you@x at <Team>" and STORED PROFILES
thestage config switch-profile   # interactive pick
```

Symptom of the wrong profile: `instance rented ls` shows nothing (or only old, terminated
machines), or `project task ls` says the project cannot be found.

## Getting help

Every level has `--help`; it is the source of truth for flags:

```bash
thestage --help
thestage project --help
thestage project run --help
thestage instance rented create --help    # also lists allowed GPU and provider names
```

`thestage -D <command>` (`--debug`) prints full Python tracebacks. App logs live in the
directory printed by `thestage config get` (macOS: `~/Library/Logs/thestage`).

## IDs, names and paging

* Most commands accept an ID **or** a name: `-cid/-cn` (container), `-rid/-rn` (rented
  instance), `-sid/-sn` (self-hosted), `-pid/-pn` (project). Inside a cloned project
  directory the project is implied (`.thestage/project.json`), elsewhere pass `-pid/-pn` or
  `-wd <project dir>`.
* Listings show 5 rows and then **prompt `Go to next page (0 to exit)?`**. In scripts use a
  big page and answer the prompt: `printf '0\n' | thestage container ls -r 100`.
* Listings hide finished objects by default; add `--status all` (`-s all`).

## Non-interactive use (scripts, agents)

The CLI prompts in many places. Feed answers on stdin and keep stdout parseable:

| Prompt | Where | Answer |
|---|---|---|
| `Go to next page (0 to exit)?` | every `ls` | `0` |
| `Choose which image to use:` | `container create` without a matching `-i <repository>` | pass `-i`; otherwise the index from `container image ls` |
| `Would you like to set '<c>' as a default container…?` | first `project run -cn <c>` | `y` / `n` |
| `Active branch … has uncommitted changes …` → `Commit changes?` + `Provide commit message` | `project run` without `-sa` | prefer `-sa` and commit yourself |
| `Continue?` | `project run` in detached HEAD with local changes | `n`; check out a branch |
| `Selection is required for: …` / `Offer #` | `instance rented create` | see `thestage-instances` |

`thestage project run` streams logs until the task ends, and an interrupt (Ctrl+C, an agent's
tool timeout) **cancels the task**: agents always add `-nl` and read logs separately.
The page prompt appears only when there is more than one page.
The `thestage-tasks` skill ships `.agents/skills/thestage-tasks/scripts/ts.sh`: prompt-free run/status/logs/wait/watch.

## SSH access and keys

`connect`, `container upload/download` and `instance rented connect` use SSH to the
**host** as the instance's host user, which the platform supplies (`ubuntu` on our Nebius
instances). Self-hosted: `-u <user>`, default `root`.

```bash
ssh-add ~/.ssh/<your_key>                     # the CLI uses your ssh-agent by default
ssh-add -l                                    # check what the agent offers
thestage config upload-ssh-key ~/.ssh/<key>.pub                   # register on the platform
thestage config upload-ssh-key ~/.ssh/<key>.pub -rn <instance>    # and on one rented instance
thestage connect <instance|container|task>    # interactive shell (or log stream for a task)
thestage container connect -cn <name> -pk ~/.ssh/<key>            # pin a key for that host
```

`-pk` stores the key path for that IP; `-fsa` forces the agent again and clears it.
A new host also needs its host key accepted once (`ssh ubuntu@<ip>` and answer `yes`, or
`ssh-keyscan <ip> >> ~/.ssh/known_hosts`); otherwise non-interactive connects fail with
`Host key verification failed`.

Team etiquette: run workloads as **tasks**, not inside interactive shells. Tasks are visible
in `project task ls`, get logs, install `requirements.txt`, and respect the container queue;
processes started by hand over SSH are invisible to everyone else and can hold GPUs.

## Safety rules for agents

* Never print or commit tokens (`config get`, `~/.thestage/config.json`, `.modal.toml`, HF tokens).
* Destructive or paid actions need explicit human approval: `instance rented create -f`,
  `instance rented restart`, `container restart`, cancelling other people's tasks,
  `instance rented terminate`, `container delete`, `project delete`, `project reset`.
* Before deleting or overwriting, look at the target (`container info`, `task ls`).
