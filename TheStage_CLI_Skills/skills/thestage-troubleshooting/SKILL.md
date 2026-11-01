---
name: thestage-troubleshooting
description: Diagnose TheStage CLI and task failures by error message - wrong team profile, missing project, image prompts, upload mapping errors, SSH and host-key failures, log streaming errors, flags swallowed by `project run`, missing python/venv/packages in images, file-descriptor limits, GPUs used by other containers, stale cancels, and shell pitfalls. Use whenever a thestage command or task fails.
---

# Troubleshooting

First moves for any failure:

```bash
thestage -D <same command>                  # full traceback
thestage config get                         # right team profile? (token is printed: don't share)
thestage project task logs <task-id> -n 200 # the task's own output, also after it ended
```

## CLI and platform

| Symptom | Cause | Fix |
|---|---|---|
| `instance rented ls` / `project ls` shows nothing or only old items | wrong active team profile | `thestage config switch-profile` |
| `No project found at path …` / `Provide the project ID or name …` | not inside a cloned project dir, or the dir was re-cloned/deleted | `cd` into the clone, or pass `-pid/-pn` (`-wd` for run/config) |
| `Image '…' was not found. Select from available images` then `Invalid input. Enter a number.` | `-i` must be the repository only (`thestageai/qlip-elastic`), not `repo:tag` or a registry path; then stdin answered the index prompt with text | `-i <repository>` from `container image ls`, or pipe the index: `printf '1\ny\n' \| thestage container create …` |
| `Error connecting to server or Docker container at <ip> as ubuntu` | no usable key in the ssh-agent for that host | `ssh-add ~/.ssh/<key>`; register it: `thestage config upload-ssh-key <key>.pub -rn <instance>` |
| `Host key verification failed` (non-interactive connect) | host key not in `known_hosts` | connect once interactively, or `ssh-keyscan <ip> >> ~/.ssh/known_hosts` |
| `Cannot find matching container volume mapping for specified file path` | upload target is not a mounted path | upload under `/mount/...` or `/project/shared/...` |
| `Task must be in status 'running' to stream real-time logs` | task finished | `thestage project task logs <id> -n 200` |
| `No such option: --lr` (any of your script's flags) | command not quoted; CLI parsed the flags | one quoted string, or `--` before the command |
| Variables you exported locally are missing in the task | local env is not forwarded | `env A=1 B=2 cmd` in the command, or a wrapper script |
| Task ran old code | `-sa` with an unpushed `HEAD`, or the wrong branch | `git push`; check `git log -1` against the task's commit; `project checkout -tid <id>` |
| `Current commit created in detached HEAD state` | committed while detached | `thestage project checkout -b <branch>`, cherry-pick, push |
| File refused on run / commit | file > 500 KB in the project repo | move it to storage, add it to `.gitignore` |
| Default container prompt every run / "Default container settings were reset" | first use, or default container was deleted | answer once, or `project config set-default-container -cn …`; always pass `-cn` in scripts |
| Several tasks "scheduled", nothing running | serial queue: one task per container | wait, cancel, or use more containers |
| Image lacks tools you expected (TensorBoard, `python`, `venv`, a torch version) | a convenience pick of image (prompt option 1, a teammate's image) | probe the image first (`thestage-containers` → Images); recreate the container on the right image |
| A listing hangs in a script | waiting on `Go to next page (0 to exit)?` | `printf '0\n' \| thestage … ls -r 100` |

## Inside tasks (images and runtime)

| Symptom | Cause | Fix |
|---|---|---|
| `python: command not found` | image has only `python3` | call `python3` |
| `ModuleNotFoundError` for your own package | repo root / `src` not importable | `export PYTHONPATH=$PWD:$PWD/src` in a wrapper, or `pip install -e .` |
| `The virtual environment was not created successfully because ensurepip is not available` | image Python lacks venv/ensurepip | `pip install uv && uv venv --python 3.12 <path>` |
| venv on storage works in one container, `bad interpreter` in others | uv put the interpreter in that container's home | build with `UV_PYTHON_INSTALL_DIR=<storage>/uv-python` (and `UV_CACHE_DIR`) |
| `OSError: [Errno 24] Too many open files` | low fd soft limit; code keeps many files/mmaps open | `ulimit -n "$(ulimit -Hn)"` in the wrapper; open files lazily |
| vLLM: `TokenizersBackend has no attribute all_special_tokens_extended` | transformers 5.x with vLLM 0.11 | pin `transformers==4.57.1` in that venv |
| `huggingface-cli: No such file or directory` | huggingface_hub ≥ 1.0 removed it | `hf download …` or `snapshot_download()` from Python |
| Downloads of HF models/datasets repeat every task | `HF_HOME` on container disk | `export HF_HOME=/mount/fs0/<you>/hf` |
| Task fails after a few seconds, other containers' tasks fine | container-local state assumed (venv, cache, file) | keep state on storage; probe with a tiny task |

## GPUs

| Symptom | Cause | Fix |
|---|---|---|
| Your reserved GPUs show memory in use / utilisation at task start | another container on the host was created **without** `--gpu-number` and uses all GPUs | `thestage-instances` → `gpu_capacity.py` to find it; ask the owner to recreate it with a GPU limit |
| Step time 2× right after a cancel + relaunch | the canceled process is still alive | wait ~60 s after cancel; check `nvidia-smi` in the new task's first lines |
| Wrong number of GPUs or CPUs | container limits | `nproc`, `nvidia-smi` in a task; recreate with `-gpun/-cpun` |
| CUDA arch errors on RTX PRO 6000 (Blackwell) | build without `sm_120` | use torch built for CUDA ≥ 12.8: `python3 -c "import torch; print(torch.cuda.get_arch_list())"` |

## Shell pitfalls (zsh on macOS)

* zsh does not word-split `$var`: `for id in $ids` runs once with the whole string. Use
  `bash -c '…'`, arrays, or `xargs`.
* `sed -i ''` with `#` delimiters breaks on `#` in the text: use a Python one-liner or an editor.
* Chains like `cmd1 && cmd2; thestage project run …`: the launch runs even if `cmd1` failed.
  Use `&&` all the way to the launch.
