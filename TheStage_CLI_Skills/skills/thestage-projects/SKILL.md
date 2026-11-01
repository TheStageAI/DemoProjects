---
name: thestage-projects
description: Work with TheStage projects - clone or init the project repo, move code into it, create or switch branches, understand exactly which commit a task runs (auto-commit, push, -sa, -hash, -fa), the 500 KB file limit, default containers, pull and reset. Use before launching tasks from a repo or when a task ran the wrong code.
---

# Projects: repo, branches, and the commit a task runs

A TheStage project **is a git repository** (hosted on GitHub by TheStage, accessed with a
per-project deploy key). Containers never see your laptop: every task checks out **one
commit** of this repo. Getting the commit right is the whole game.

## Clone, init, inspect

```bash
mkdir my-proj && cd my-proj
thestage project clone -pn <ProjectName>        # or -pid project-xxxx; target dir must be empty
thestage project init  -pn <ProjectName> -r <public git url>   # seed from a public repo
thestage project config get                     # project id, repo url, deploy key, default container
printf '0\n' | thestage project ls -r 50        # projects of the active team (see profiles)
```

`.thestage/project.json` marks the directory as a project (keep it out of git; the clone adds
`/.thestage/` to `.gitignore`). A project name can exist in several teams: check the active
profile if the wrong project (or none) is found.

Moving existing code into a fresh project: copy the files without `.git`, commit, push.
Files over **500 KB cannot enter the project repo** (the CLI warns and refuses on auto-add):
keep data, weights and generated artefacts on storage (`thestage-storage`) and list them in
`.gitignore`.

```bash
rsync -a --exclude .git --exclude .thestage --exclude '__pycache__' --exclude '*.so' \
      --exclude '<big dirs>' ../old_repo/ ./
find . -path ./.git -prune -o -type f -size +500k -print     # must print nothing
git add -A && git commit -m "Import code" && git push -u origin main
```

## Branches

The project directory is a normal git checkout with the deploy key configured
(`core.sshCommand`), so plain git works:

```bash
git checkout -b exp/new-loss && git push -u origin exp/new-loss   # create + publish a branch
thestage project checkout -b exp/new-loss    # switch (fetches); "-b /" = back to main
thestage project checkout -tid <task-id>     # check out exactly what a past task ran (detached)
thestage project pull                        # git pull
thestage project reset                       # git fetch && git reset --hard origin/<branch>: DISCARDS local work
```

## Which commit does `project run` execute?

From the CLI source (0.7.16), in order:

1. **Default (no flags):** if the working tree has changes, it shows the diff stat, asks
   *Commit changes?* and a commit message, commits **all changes including untracked files** (files
   > 500 KB abort the run), **pushes the current branch**, then runs **local `HEAD`**.
   No changes: it pushes and runs `HEAD`.
2. **`-sa` / `--skip-autocommit`:** no commit and **no push**: runs local `HEAD` as is. If
   `HEAD` is not on the remote, the task cannot check it out. Rule: `git push` first.
3. **`-hash <sha>`:** runs that exact commit. The CLI only checks it exists locally and pushes
   nothing: push it first.
4. **`-fa a.py,b.py`:** auto-commit only these files.

`-sa`, `-hash` and `-fa` are mutually exclusive. A detached `HEAD` with commits made while
detached is refused ("Current commit created in detached HEAD state"); use
`project checkout -b <branch>` first.

Recommended for reproducible work (and for agents): commit and push yourself, then run with
`-sa`. The task title defaults to the commit message; set `-t <title>` for readable task lists.

Working on the project from two checkouts (laptop + teammate) is plain git: pull before you
commit, or the push in step 1 is rejected.

## Default container

The first `project run -cn <container>` asks whether to make it the project default for this
checkout. With a default set, `project run "<cmd>"` needs no `-cn`.

```bash
thestage project config set-default-container -cn <container>
thestage project config set-default-container --unset
```

Pass `-cn` explicitly in scripts anyway: defaults are per checkout, and a run whose default
container was deleted exits with an error ("Default container settings were reset").

## Delete (restricted, irreversible)

`thestage project delete` removes the project and its repo for everyone. Human approval only.
