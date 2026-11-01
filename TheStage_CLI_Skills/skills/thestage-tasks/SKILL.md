---
name: thestage-tasks
description: Run and supervise work on TheStage - launch tasks with `thestage project run` (quoting, flags, interactive prompts, logs on or off), list tasks, read logs of running and finished tasks, cancel safely, write watchers that wait for completion or catch crashes, run experiments in parallel across containers, and handle environment, requirements and secrets inside tasks.
---

# Tasks

A task = one shell command executed at one commit of the project repo, inside one container.

## Lifecycle

```
project run ──► scheduled (queued behind the container's current task)
            ──► preparing: clone commit → /var/lib/thestage_daemon/tasks/<id>/code,
                           pip install -r requirements.txt (repo root, if present)
            ──► running:   your command, cwd = that code dir
            ──► completed (exit 0) | failed (exit ≠ 0) | canceled
```

* **Serial queue per container.** A new task waits until the current one ends. Parallel work
  needs several containers (`thestage-containers`).
* **Fresh checkout every time.** Nothing written into the code dir survives; write outputs to
  mounted storage (`/mount/fs0/...`).
* **Your local environment does not travel.** `FOO=1 thestage project run ...` does nothing
  remotely; put variables in the command (`env FOO=1 python ...`) or in a wrapper script in
  the repo.
* Which commit runs: see `thestage-projects` (commit and push, then use `-sa`).

## Launch

```bash
thestage project run -cn <container> -t "<title>" -sa -nl "python train.py --lr 3e-4 --run r1"
```

* **Options first, then the command as ONE quoted string.** Flags after an unquoted command
  are parsed as CLI options (`No such option: --lr`). Alternative: `... -nl -- python train.py --lr 3e-4`.
  See *Quoting* below.
* `-nl` returns right after scheduling; without it the CLI streams logs until the task ends
  (Ctrl+D detaches, Ctrl+C **cancels the task**). **Agents: always pass `-nl`**: a tool
  timeout or SIGINT on a streaming run cancels the task.
* With `--` the remaining words are joined by single spaces, so inner quoting is lost: use the
  one-string form for anything with quotes.
* Interactive prompts you can meet: *set default container?* (first `-cn` use), *commit
  uncommitted changes?* + *commit message* (without `-sa`), *continue in detached HEAD?*.
  In scripts: `printf 'n\n' | thestage project run -nl -sa ...`, or use `.agents/skills/thestage-tasks/scripts/ts.sh`.
* Compound commands: wrap in `bash -c '...'`, or better, commit a script and run
  `bash scripts/job.sh args`. Keep logic in the repo, not in the launch string.
* The image may lack conveniences you expect (e.g. no `python`, only `python3`). Probe once
  with a tiny task and encode fixes in a wrapper script.

## Quoting: what your shell expands vs what the container gets

Your **local** shell parses the line first; the CLI sends the resulting string to the
container, where `bash` runs it.

```bash
# 1. Whole command in quotes, CLI options before it
thestage project run -nl -sa -cn c0 "python3 train.py --lr 3e-4 --run r1"

# 2. Single quotes: nothing expands locally; $HOME, $(...), globs and ; run in the container
thestage project run -nl -sa -cn c0 'ls /mount/fs0/data/*.bin | wc -l; echo $HOSTNAME'

# 3. Double quotes: $VARS expand on YOUR machine before sending (good for local values)
RUN=r7; thestage project run -nl -sa -cn c0 "python3 train.py --run $RUN"

# 4. Several commands, pipes, cd, env: wrap in bash -c '...' inside double quotes
thestage project run -nl -sa -cn c0 "bash -c 'cd sub && env A=1 python3 x.py | tee /mount/fs0/log.txt'"

# 5. Anything longer: commit a script and run it
thestage project run -nl -sa -cn c0 "bash scripts/job.sh r1 3e-4"
```

| Mistake | What happens |
|---|---|
| `thestage project run python3 x.py --lr 1` (no quotes) | `--lr` is taken as a CLI option: `No such option` |
| `"... $HOME ..."` in double quotes | your laptop's `$HOME` is sent |
| `'... '$RUN' ...'` mixing quotes | works, but hard to read: prefer a script |
| quotes inside JSON or regex | escape once more, or put it in a script |

Check what was actually sent: the first lines of the task log, or print `"$@"` at the top
of your wrapper script.

## requirements.txt and the image

* Before **every** task the platform runs `pip install -r requirements.txt` from the **repo
  root** of the task's commit. The log shows it, then `✅ Required Python packages
  installed`, then `starting execution`. An install failure fails the task before your
  command runs.
* Packages land in the **container**, so later tasks in the same container find them already
  installed (fast). A new container installs them again on its first task.
* **Do not list what the image already provides** (`torch`, CUDA libraries): a resolver
  "upgrade" can replace the image's CUDA build. Leave a comment instead:
  `# torch comes with the container image`.
* Pin versions that change behaviour (`lm_eval==0.4.x`, `transformers<5` if a dependency needs
  it); leave stable small ones unpinned.
* Packages that conflict with the image (another torch, vLLM) go into a separate venv on
  storage, called by absolute path (see below).
* Changing `requirements.txt` is a code change: commit and push it before the run.
* No `requirements.txt` → no install step. A quick probe:
  `"bash -c 'python3 -c \"import torch, sys; print(sys.version, torch.__version__, torch.version.cuda)\"; pip list | head -50'"`.

## Observe

```bash
printf '0\n' | thestage project task ls -r 20      # ID, TITLE, STATUS, CONTAINER ID, STARTED AT, FINISHED AT
thestage project task logs <task-id>               # live stream (running tasks only)
thestage project task logs <task-id> -n 200        # last 200 lines; works for finished tasks too
thestage connect <task-id>                         # attach to the live log stream
```

`logs` without `-n` on a finished task fails with
`Task must be in status 'running' to stream real-time logs`: add `-n`.

## Cancel

```bash
thestage project task cancel <task-id>
```

Canceled is a status, not proof the process died: the old process can live for tens of
seconds. Before launching the replacement on the same GPU, wait ~60 s and check `nvidia-smi`
in the new task's first log lines. A doubled step time means the old process is still alive.

## Prompt-free helper and watchers

`.agents/skills/thestage-tasks/scripts/ts.sh` (run it inside the project directory):

```bash
id=$(.agents/skills/thestage-tasks/scripts/ts.sh run <container> train-r1 "python train.py --run r1")
.agents/skills/thestage-tasks/scripts/ts.sh status $id            # scheduled|running|completed|failed|canceled
.agents/skills/thestage-tasks/scripts/ts.sh logs $id 100
.agents/skills/thestage-tasks/scripts/ts.sh wait $id && echo ok   # exit 0 only if completed
.agents/skills/thestage-tasks/scripts/ts.sh watch $id 'Error|Traceback|loss' 60   # print new matching lines, exit at the end
.agents/skills/thestage-tasks/scripts/ts.sh ls 10
```

Watcher rules that save hours:

1. **Check a healthy start** 5–10 min after launch: the first training/eval lines exist, the
   learning rate and step time look right, and the GPU was empty at start. "Scheduled" is
   not "running".
2. A watcher must end on success **and** on failure or cancel (`wait` and `watch` do), and
   should print the last log lines when it ends.
3. Chain the next step to completion (`ts.sh wait $id && ts.sh run ...`) instead of polling by
   hand.
4. Log progress with timestamps inside your job (`print(time.strftime('%H:%M:%S'), ...)`), and
   print GPU UUID / PCI bus id at start: logs are your only window into the container.

## Parallel experiments

```bash
for i in 0 1 2 3; do
  .agents/skills/thestage-tasks/scripts/ts.sh run <you>-g$i "sweep-lr$i" "python train.py --lr ${LRS[$i]} --run sweep-$i"
done
```

One container per GPU, outputs to `/mount/fs0/<you>/<project>/runs/<run>` so any container
(and the next task) can read them.

## Venvs and secrets

* Tools that need their own stack (e.g. vLLM with a different torch): build a venv **on
  mounted storage** once and call it by absolute path. Put the interpreter there too
  (`uv venv` with `UV_PYTHON_INSTALL_DIR` on storage); a venv whose Python lives in one
  container's home is dead in every other container (`bad interpreter`).
* Secrets never go in the repo or the launch string (both are stored and visible in the
  task list). Upload a token file to storage once (`thestage container upload`), `chmod 600` it
  from a task, and read it from your script.
