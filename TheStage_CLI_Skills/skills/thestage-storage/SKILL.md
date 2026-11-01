---
name: thestage-storage
description: Plan and use storage on TheStage - network file systems and their region rule, attaching an existing or new file system to an instance, mounting it into containers, the per-project /project/shared folder, a container-independent data layout for datasets, checkpoints, venvs and caches, moving data in, and keeping secrets out of reach.
---

# Storage

## Three places data can live

| Where | Path in container | Survives | Shared with |
|---|---|---|---|
| **File system** (network storage) | wherever you mount `/mnt/fs/<name>` (e.g. `/mount/fs0`) | containers, instances | every container on every instance that mounts it (whole team) |
| **Project shared dir** | `/project/shared` | container deletion | containers of **this project on this host** only |
| **Container disk** | everything else (`/root`, `/workspace`, `/tmp`) | nothing: gone with the container | nobody |

Rule: anything you want tomorrow (datasets, checkpoints, eval results, venvs, model caches)
goes on the **file system**. Container disk is for scratch and caches you can rebuild.

## File systems and regions

* A file system lives in **one region** and can be attached **only to instances in the same
  region** (e.g. `uk-south2`). Choose the instance region from the marketplace table
  (`thestage-instances` → offers) to match your data, not the other way round.
* Once attached, it is mounted **on the host** at `/mnt/fs/<file-system-name>`
  (e.g. `/mnt/fs/shared-fs-uk`). Containers see it only through `-v`:
  `thestage container create ... -v /mnt/fs/shared-fs-uk:/mount/fs0`.
* CLI 0.7.16 has **no file-system commands**: creating a file system and attaching it to an
  instance are done in the web app (app.thestage.ai). Then verify from a task or host:
  `df -h /mnt/fs/*` on the host, `df -h /mount/fs0` in a container.
* An existing container cannot gain a mount: recreate it with the extra `-v`.

## A container-independent layout

```
/mount/fs0/<you>/
  <project>/data/        datasets, token files (hot copies of the main data)
  <project>/ckpt/<run>/  checkpoints
  <project>/evals/       eval outputs
  <project>/logs/        training logs, server logs
  hf/                    HF_HOME: model and dataset cache shared by all your tasks
  venvs/<name>/          extra Python environments (+ uv-python/, uv-cache/)
  .secrets/              tokens, mode 700/600
```

Point code at it with one link at task start, so paths stay stable:
`ln -sfn /mount/fs0/<you>/<project>/data /data`.

## Bringing data in

* From the internet or another cloud: download **inside a task**, straight to the file system
  (fastest, no laptop in the path).
* From a laptop: `thestage container upload <file-or-folder> <container>:/mount/fs0/...`
  (`thestage-containers`; folders are copied recursively).
* From another provider's object store: run its CLI or SDK in a task with credentials read
  from `.secrets/`. Make the copy resumable (skip files of equal size) and log MB/s.
* Very large corpora: copy a working subset (a few parts per corpus) first and pull the rest
  in the background.

## Secrets

The file system is readable by everyone who can mount it (the whole team, root in every
container). Keep secrets to a minimum there:

```bash
thestage container upload ~/.some_token <container>:/mount/fs0/<you>/.secrets/some_token
# then, from a task:
chmod 700 /mount/fs0/<you>/.secrets && chmod 600 /mount/fs0/<you>/.secrets/*
```

`/project/shared` is narrower (one project, one host) if a token is only needed there. Never put
secrets in the repo, in the launch command, or in task logs.
