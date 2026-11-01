---
name: thestage-containers
description: Create and manage TheStage containers - choose image, GPU and CPU limits, shared memory, volume mounts and ports; list, inspect, start, stop, restart, delete; read container logs; upload and download files; and split one big container into several small ones. Use whenever you need a place to run tasks.
---

# Containers

A container is a Docker container on an instance **attached to your project**
(`thestage-instances`). Tasks run inside it, **one at a time**: the container is a serial task
queue. Need N things at once? Create N containers (one per GPU is a good default for
single-GPU jobs).

## Create

```bash
cd <project dir>
printf '0\n' | thestage container image ls -r 50          # images you may use
thestage container create \
    -cn <name> \
    -rn <instance-name> \
    -i thestageai/qlip-elastic \
    -gpun 1 \
    -cpun 24 \
    -shm 16g \
    -v /mnt/fs/<fs-name>:/mount/fs0 \
    -p 8000:8000
```

| Flag | Meaning | Advice |
|---|---|---|
| `-cn` | container name | unique and descriptive: `<you>-<project>-g0` |
| `-rn/-rid`, `-sn/-sid` | target instance | must be attached to the project |
| `-i` | image **repository** | Exactly the `IMAGE` column of `image ls` **without the tag**, e.g. `-i thestageai/qlip-elastic`. `repo:tag` or the registry path does not match (`Image '…' was not found`) and drops to the prompt; a repository with several tags prompts for the tag. In 0.7.16 only the **first 5** images are searched. See *Images* |
| `-gpun` | GPUs reserved | **Always set it.** Without it the container has no limit and sees every GPU on the host, including GPUs the platform gives to other containers |
| `-cpun` | CPUs | without it there is no limit; size data jobs here (e.g. half the host) |
| `-shm` | /dev/shm | default 5 % of host RAM (per help); PyTorch DataLoader workers need several GB (`16g`–`64g`) |
| `-v host:ctr` | bind mount, repeatable | file systems live on the host at `/mnt/fs/<name>`; mount them, keep data there |
| `-p host:ctr` | port mapping, ranges allowed | needed only to reach a server from outside the host |

Every container also gets `/project/shared` (per project and host, survives container
deletion, not shared across hosts) and `/var/lib/thestage_daemon/tasks` (task checkouts).

Wait until it runs, then verify the hardware with a tiny task:

```bash
for i in $(seq 60); do s=$(thestage container info -cn <name> | grep '^STATUS'); [[ $s == *running* || $s == *fail* ]] && break; sleep 10; done; echo "$s"
thestage project run -nl -sa -cn <name> -t gpu-check \
  "bash -c 'nproc; nvidia-smi --query-gpu=index,uuid,pci.bus_id,memory.used,utilization.gpu --format=csv; df -h /mount/fs0'"
```

`memory.used` must be ~0 MiB on reserved GPUs. If not, an unlimited container on the same host
is using them (`thestage-instances` → free GPUs).

## Images: choose deliberately

The image decides Python, CUDA, torch, preinstalled tools (TensorBoard, `python` alias,
`venv`) and what every task has to install. A container cannot change its image: the
wrong pick costs a recreate later. Do not just take prompt option `1`, and do not copy a
teammate's image without checking what is in it.

```bash
printf '0\n' | thestage container image ls -r 50     # the images registered for the ACTIVE TEAM
```

* The list is **per team** (profile) and holds only images registered on the platform. The CLI
  cannot add images; registering a new one (your team's main training image) happens in the
  platform outside the CLI. If the image you expect is missing, check the active profile first.
* Pass the repository with `-i`; pick the tag at the prompt if there are several.
* Verify a new image once with a probe task before running real work:

```bash
thestage project run -nl -sa -cn <name> -t image-probe "bash -c '
  cat /etc/os-release | head -2; which python python3 pip; python3 -V
  python3 -c \"import torch; print(torch.__version__, torch.version.cuda, torch.cuda.get_arch_list())\"
  python3 -m venv /tmp/v && echo venv-ok; pip list 2>/dev/null | grep -iE \"^(torch|tensorboard|numpy|transformers|vllm) \"
  nvidia-smi --query-gpu=name,driver_version --format=csv,noheader'"
```

* Record the image and tag next to the container name in your notes; `container info` shows
  the image, `container ls` too.

Gaps you can patch per task (they are cheap): missing packages → `requirements.txt`; no
`python` → call `python3`. Gaps that justify a different image: wrong CUDA or torch, wrong
Python major version, missing system libraries.

### TensorBoard (and other long-running servers)

A server started as a task occupies that container's queue for as long as it runs. Run it in a
**separate small container** with a published port, reading logs from shared storage:

```bash
thestage container create -cn <you>-tb -rn <instance> -i <repository> -gpun 0 -cpun 4 \
    -v /mnt/fs/<fs>:/mount/fs0 -p 6006:6006
thestage project run -nl -sa -cn <you>-tb -t tensorboard \
    "bash -c 'pip install -q tensorboard && tensorboard --logdir /mount/fs0/<you>/<project>/logs --host 0.0.0.0 --port 6006'"
# open http://<instance ip>:6006 (ip from `thestage instance rented ls`)
```

Training containers then only write event files to `/mount/fs0/<you>/<project>/logs/<run>`.
Whether `-gpun 0` is accepted and whether port 6006 is reachable from outside depends on the
platform and the host firewall: check once; otherwise use an SSH tunnel
(`ssh -L 6006:localhost:6006 ubuntu@<ip>`).

## Inspect and operate

```bash
printf '0\n' | thestage container ls -r 100              # running/starting
printf '0\n' | thestage container ls -r 100 -s all       # incl. stopped/failed/terminated
printf '0\n' | thestage container ls -pn <project>
thestage container info    -cn <name>     # status, image, instance, shm, mounts (no GPU count)
thestage container logs    -cn <name> -n 200            # docker logs (not task logs)
thestage container stop    -cn <name>
thestage container start   -cn <name>
thestage container restart -cn <name>                   # kills the running task
thestage container delete  -cn <name>                   # irreversible
thestage container connect -cn <name>                   # interactive shell (inspection only)
```

`info` shows no CPU/GPU limits; read them from a task (`nproc`, `nvidia-smi`), and record
the flags you used in your own notes.

## Resize = recreate

Limits cannot be changed in place. Recreating is cheap **if nothing lives only in the
container**: data, checkpoints, venvs and caches belong on mounted storage.

1. Wait for (or cancel) its tasks: `printf '0\n' | thestage project task ls`.
2. `thestage container delete -cn <old>` and wait until `info` reports nothing.
3. `container create` with the new limits (same mounts).
4. Re-run the gpu-check task.

One 4-GPU container → four 1-GPU containers (four independent queues):

```bash
for g in 0 1 2 3; do
  thestage container create -cn <you>-g$g -rn <instance> -i <repository> -gpun 1 -cpun 24 -shm 16g -v /mnt/fs/<fs>:/mount/fs0 < /dev/null
done
```

## Files in and out

```bash
thestage container upload   ./model.pt  <container>:/mount/fs0/<you>/ckpt/model.pt   # file (last part has a '.')
thestage container upload   ./run_dir   <container>:/mount/fs0/<you>/runs          # folder, recursive -> runs/run_dir
thestage container upload   ./run_dir/  <container>:/mount/fs0/<you>/runs/r1       # trailing / = contents only
thestage container download <container>:/mount/fs0/<you>/evals/result.json ./
```

* Transfers go over SFTP to the **host** as the instance's host user (from the platform:
  `ubuntu` on our Nebius instances; `-u` only for self-hosted). The SFTP server runs with `sudo`
  on the host. Load your key into the agent first (`ssh-add`; see `thestage-cli`).
* The destination must be inside a **mounted path** (`/mount/fs0/...`, `/project/shared/...`).
  Container-only paths such as `/root` fail with
  `Cannot find matching container volume mapping for specified file path`.
* Folders upload recursively. A destination whose last part contains a `.` is treated as a
  file name, anything else as a folder: name folders without dots.
* Large data: write it to the file system from a task (download in the container) rather than
  pushing it from a laptop.
