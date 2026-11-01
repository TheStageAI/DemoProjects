#!/usr/bin/env python3
"""Free GPUs on every online rented instance.

    python3 gpu_capacity.py              # one row per instance
    python3 gpu_capacity.py --detail     # plus one row per GPU
    python3 gpu_capacity.py --instance rtx-6000-pro-8x-2

The platform API does not report GPU allocations, so this reads each host directly over SSH
(user ``ubuntu``, keys from your ssh-agent; see the thestage-cli skill for key setup):

* ``nvidia-smi``: memory, utilisation and compute processes per GPU;
* ``docker inspect``: which GPUs each container reserved. A container created without
  ``--gpu-number`` reserves nothing but can use *every* GPU on the host: it is reported as
  ``unlimited`` and makes every GPU on that host "shared".

A GPU is *free* when no container reserved it, no unlimited container exists, it runs no
compute process and uses under 1 GiB. Only read-only commands run on the hosts.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

REMOTE = r"""
echo '##GPU'; nvidia-smi --query-gpu=index,uuid,memory.used,memory.total,utilization.gpu,name --format=csv,noheader,nounits
echo '##PROC'; nvidia-smi --query-compute-apps=gpu_uuid,pid,used_memory --format=csv,noheader,nounits
echo '##CTR'
D="docker"; $D ps -q >/dev/null 2>&1 || D="sudo -n docker"
for c in $($D ps -q 2>/dev/null); do
  $D inspect --format '{{.Name}}|{{json .HostConfig.DeviceRequests}}' "$c" 2>/dev/null
done
"""


def online_instances() -> list[dict]:
    out = subprocess.run(["thestage", "instance", "rented", "ls", "-r", "100"], input="0\n",
                         capture_output=True, text=True, timeout=120).stdout  # fmt: skip
    rows = []
    for line in out.splitlines():
        cells = [c.strip() for c in line.split("║")[1:-1]]
        if len(cells) >= 7 and cells[0].startswith("instancerented-"):
            rows.append({"id": cells[0], "name": cells[1], "status": cells[2], "gpu": cells[5], "ip": cells[6]})
    return [r for r in rows if r["status"] == "online" and "NVIDIA" in r["gpu"] and r["ip"]]


def probe(ip: str) -> str:
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new", "-o",
                        "ConnectTimeout=15", f"ubuntu@{ip}", "bash -s"], input=REMOTE,
                       capture_output=True, text=True, timeout=120)  # fmt: skip
    if r.returncode != 0 and "##GPU" not in r.stdout:
        raise RuntimeError(r.stderr.strip().splitlines()[-1] if r.stderr.strip() else f"ssh exit {r.returncode}")
    return r.stdout


def num(x: str) -> int:
    """nvidia-smi prints [N/A] for some fields (MIG, some boards)."""
    try:
        return int(float(x))
    except ValueError:
        return -1


def parse(text: str) -> tuple[list[dict], list[dict]]:
    gpus, procs, ctrs, part = [], set(), [], None
    for line in text.splitlines():
        if line.startswith("##"):
            part = line[2:]
            continue
        if not line.strip():
            continue
        if part == "GPU":
            i, uuid, used, total, util, name = [x.strip() for x in line.split(",", 5)]
            gpus.append({"index": num(i), "uuid": uuid, "used": num(used), "total": num(total),
                         "util": num(util), "name": name, "owner": None, "procs": 0})  # fmt: skip
        elif part == "PROC":
            procs.add(line.split(",")[0].strip())
        elif part == "CTR" and "|" in line:
            name, req = line.split("|", 1)
            for dr in json.loads(req) or []:
                if "gpu" not in json.dumps(dr.get("Capabilities") or []):
                    continue
                ids, count = dr.get("DeviceIDs") or [], dr.get("Count") or 0
                # --gpus all -> Count -1 (sees every GPU); --gpus N -> Count N, Docker picks the GPUs
                ctrs.append({"name": name.lstrip("/"), "ids": ids, "unlimited": not ids and count == -1,
                             "count": count if not ids and count > 0 else 0})  # fmt: skip
    by_key = {g["uuid"]: g for g in gpus} | {str(g["index"]): g for g in gpus}
    for c in ctrs:
        for d in c["ids"]:
            if d in by_key:
                by_key[d]["owner"] = c["name"]
    for g in gpus:
        g["procs"] = int(g["uuid"] in procs)
    return gpus, ctrs


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--detail", action="store_true")
    p.add_argument("--instance", help="only this instance name")
    a = p.parse_args()
    insts = [i for i in online_instances() if not a.instance or i["name"] == a.instance]
    if not insts:
        sys.exit("no online GPU instance found (thestage instance rented ls)")
    print(f"{'INSTANCE':28} {'GPU':24} {'TOTAL':>5} {'RESERVED':>8} {'BUSY':>4} {'FREE':>4}  NOTE")
    for inst in insts:
        try:
            gpus, ctrs = parse(probe(inst["ip"]))
        except Exception as e:  # noqa: BLE001
            print(f"{inst['name']:28} {'?':24} {'?':>5} {'?':>8} {'?':>4} {'?':>4}  ssh failed: {e}")
            continue
        unlimited = [c["name"] for c in ctrs if c["unlimited"]]
        by_count = sum(c["count"] for c in ctrs)  # reserved by count: which GPUs is unknown
        busy = [g for g in gpus if g["procs"] or g["used"] >= 1024]
        free = [g for g in gpus if not g["owner"] and not unlimited and not g["procs"] and 0 <= g["used"] < 1024]
        free = free[: max(0, len(free) - by_count)]
        note = f"unlimited container(s): {', '.join(unlimited)} -> GPUs are shared" if unlimited else ""
        if by_count:
            note += f" {by_count} GPU(s) reserved by count (ids unknown)"
        model = re.sub(r"^NVIDIA ", "", gpus[0]["name"]) if gpus else "-"
        print(f"{inst['name']:28} {model[:24]:24} {len(gpus):>5} {sum(1 for g in gpus if g['owner']) + by_count:>8} "
              f"{len(busy):>4} {len(free):>4}  {note}")  # fmt: skip
        if a.detail:
            for g in gpus:
                state = "free" if g in free else ("busy" if g in busy else "reserved")
                print(f"    gpu{g['index']}  {state:8} {g['used']:>6}/{g['total']} MiB  util {g['util']:>3}%  "
                      f"owner {g['owner'] or ('ALL: ' + ','.join(unlimited) if unlimited else '-')}")  # fmt: skip


if __name__ == "__main__":
    main()
