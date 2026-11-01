---
name: thestage-instances
description: Monitor rented and self-hosted TheStage instances, report how many GPUs are free on each instance, list hardware-marketplace offers (GPU, region, price) without renting, rent, restart or terminate instances, and attach or detach instances to projects. Use for any "which machine / how many GPUs / what can I rent" question.
---

# Instances: monitoring, free GPUs, marketplace, rent, attach

Prerequisite: `thestage-cli` (login, active team profile, SSH agent).

## 1. List what the team has

```bash
printf '0\n' | thestage instance rented ls -r 50              # default filter: online, creating, terminating, rebooting
printf '0\n' | thestage instance rented ls -r 50 --status all # include stopped/terminated
printf '0\n' | thestage instance self-hosted ls -r 50
printf '0\n' | thestage project ls -rn <instance-name>        # projects attached to an instance
printf '0\n' | thestage container ls -r 100                   # containers (column INSTANCE NAME)
```

Columns of `rented ls`: `ID, NAME, STATUS, CPU TYPE, CPU CORES, GPU TYPE, IP ADDRESS, SHM AVAIL`.
Statuses you will see: `online`, `creating`, `starting`, `rebooting`, `stopping`, `stopped`,
`terminating`, `terminated`, `rental error`, `unreachable` (self-hosted: `awaiting setup`).

## 2. Free GPUs per instance

The platform API returns no GPU counts or allocations: not per instance, not per container.
The only ground truth is the host itself, so measure there:

```bash
python3 .agents/skills/thestage-instances/scripts/gpu_capacity.py            # one row per online GPU instance
python3 .agents/skills/thestage-instances/scripts/gpu_capacity.py --detail   # plus per-GPU state, memory, utilisation, owner
python3 .agents/skills/thestage-instances/scripts/gpu_capacity.py --instance rtx-6000-pro-8x-2
```

Output format (illustrative values):

```
INSTANCE                     GPU                      TOTAL RESERVED BUSY FREE  NOTE
rtx-6000-pro-8x-2            RTX PRO 6000 Blackwell       8        4    4    0  unlimited container(s): team-a -> GPUs are shared
rtx-6000-pro-8x              RTX PRO 6000 Blackwell       8        0    3    5
```

How it decides (read-only SSH as `ubuntu`, keys from your agent):

| State | Rule |
|---|---|
| **reserved** | a running container was created with `--gpu-number` and Docker assigned it this GPU |
| **busy** | a compute process runs on it, or it holds ≥ 1 GiB |
| **free** | not reserved, not busy, and **no unlimited container on the host** |

The last rule matters. A container created **without** `--gpu-number` reserves nothing but
sees and can use *every* GPU on the host, including GPUs the platform later hands to someone
else's limited container. The script flags such hosts. The fix is social: ask the owner to
recreate the container with `--gpu-number`.

Not tested end to end yet: the parsing is verified on sample output, but the SSH collection
step has not been run against a live host. Run it once, compare with `nvidia-smi` on the
host, and report any mismatch.

Quick manual check of one host (same data, by eye):

```bash
ssh ubuntu@<ip> 'nvidia-smi; docker ps --format "{{.Names}}" | xargs -r docker inspect --format "{{.Name}} {{json .HostConfig.DeviceRequests}}"'
```

From inside your own container you only see your own GPUs (a limited container) or all of
them (an unlimited one): `nvidia-smi --query-gpu=index,uuid,pci.bus_id,memory.used,utilization.gpu --format=csv`.
Print the UUIDs and PCI bus IDs in every task log; they map to host GPU slots.

## 3. Hardware marketplace: what can be rented, where, for how much

There is no `offers` command. `instance rented create` **without** `--force-yes` first asks
the backend for matching offers and only rents after you pick `Offer #`. With stdin closed
the prompt aborts, so the offers table is printed and nothing is rented:

```bash
bash .agents/skills/thestage-instances/scripts/offers.sh Nebius RTX6000 8 930
bash .agents/skills/thestage-instances/scripts/offers.sh Nebius H100 8 930
bash .agents/skills/thestage-instances/scripts/offers.sh Amazon H100 8 1000
bash .agents/skills/thestage-instances/scripts/offers.sh Nebius RTX6000          # missing count -> prints the allowed choices
```

Example result (2026-11-01; prices change, always re-query):

| Provider, region | GPU | CPU | RAM GB | Disk GB | $/hour |
|---|---|---|---|---|---|
| Nebius, uk-south2 / eu-south1 | 8× RTX6000 (RTX PRO 6000 Blackwell, 96 GB) | 192× Xeon 6776P | 1744 | 930 | 14.65 |
| Nebius, uk-south2 / eu-south1 | 1× RTX6000 | 24× Xeon 6776P | 218 | 465 | 1.95 |
| Nebius, eu-north1 | 8× H100 | 128× Xeon 8468 | 1600 | 930 | 37.20 |
| Amazon, us-east-1 | 8× H100 | 192× EPYC 7R13 | 2048 | 1000 | 60.80 |

Allowed values (from `--help` and backend errors): providers `Amazon`, `Nebius`; GPUs `A100`,
`A10G`, `H100`, `L40S`, `RTX6000`, `T4`. GPU counts and disk sizes depend on the offer; the
CLI prints the valid choices when one is missing (`Selection is required for: GPU count (1, 8)`).

Pick the **region** with your storage in mind: a file system attaches only to instances in
its own region (`thestage-storage`).

## 4. Rent, restart, terminate (paid / destructive: get approval)

```bash
# interactive: shows offers, you choose Offer #
thestage instance rented create -n <name> -p Nebius -g RTX6000 -ng 8 -ds 930
# non-interactive: the backend picks the offer (check the printed offer and price!)
thestage instance rented create -n <name> -p Nebius -g RTX6000 -ng 8 -ds 930 -f
printf '0\n' | thestage instance rented ls          # wait for "online"
thestage instance rented restart   -rn <name>       # power-cycle: kills every container process
thestage instance rented terminate -rn <name>       # irreversible; local disk is lost
```

Before terminate or restart: list its containers and running tasks
(`container ls`, `project task ls`); other people's work may be on it.

## 5. Attach an instance to a project

A project can only create containers on instances attached to it.

```bash
cd <project dir>                                    # or add -pid/-pn
thestage project attach-instance -rn <instance>     # repeatable: -rn a -rn b
thestage project attach-instance -sn <self-hosted>
thestage project detach-instance -rn <instance>
printf '0\n' | thestage project ls -rn <instance>   # verify
```

## 6. Connect to a host

```bash
thestage instance rented connect -rn <name>              # interactive shell as ubuntu
thestage instance self-hosted connect -sn <name> -u <user>
```

Use host shells for inspection (`nvidia-smi`, `df -h /mnt/fs/*`, `docker ps`), not to
run workloads: see `thestage-tasks`.
