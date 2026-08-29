# shellcheck shell=sh
#
# Source this (not execute) from a project mise.toml task's `run` body, then call
# `container_dispatch --project <name> --image ... --context ... --cache-key-files "..."
# --cmd "..." [extra //:_container-run flags]`. When --container was passed to the task,
# this execs `mise run //:_container-run` with the engine/bind-mount/as-user options that
# are identical across (almost) every containerized task in this repo, appending whatever
# flags the caller passed; it never returns in that case. Without --container it returns 0
# so the host command below it runs instead.
#
# --project is REQUIRED and is the whole point of this helper: it sets the bind-mount and
# the container working directory together, so a --cmd can never disagree with the mount
# it runs under. The repo root is always mounted at /src (the container gets the real
# .git, so tools that honor .gitignore behave as they do on the host) and the workdir is
# always /src/<project>. That means a --cmd should be written exactly as it would be on
# the host, relative to the project directory -- do NOT prefix it with `cd /src/<project>`,
# and where an absolute container path is unavoidable, write it as /src/<project>/...
# rather than /src/....
#
# Some lanes deliberately bind-mount nothing (frontend's `check`, `build`, `test`, and
# `fmt` without --write): they run the image's own baked source and node_modules, so they
# skip this helper and call //:_container-run directly.
#
# --- THE NESTED DEPENDENCY DIRECTORY, AND --image-dir --------------------------------
# A repo-root mount carries two kinds of content with opposite requirements: source, which
# must come from the host (live edits are the point), and dependency/tool-state
# directories nested *inside* it -- node_modules, .venv -- which must come from the image
# (pinned, right-platform, reproducible). Mounting the project necessarily shadows the
# latter with the host's copy, so `--container` silently stops meaning what it says: the
# image's `eslint`/`tsc` binary runs, but every plugin, rule and .d.ts it loads is
# resolved by walking up from the mounted tree and therefore comes from the host.
#
# The backend dodges this with an out-of-tree redirect (UV_PROJECT_ENVIRONMENT=/app/.venv,
# RUFF_CACHE_DIR=/tmp/ruff-cache) because Python's dependency root is an env var. Node has
# no equivalent -- NODE_PATH is legacy-CJS-only and ignored by ESM -- so for those lanes
# the fix has to be at the mount.
#
# Rather than mount the repo and then try to shadow the dependency directory back out
# (an anonymous volume seeded from the image does NOT work: apple/container leaves it
# empty), --image-dir inverts the mount so nothing needs shadowing:
#
#   --image-dir <path>   mount ONLY the intended host entries, individually, into the
#                        image's OWN project tree at <path>, which becomes the workdir.
#
# Every entry of the host project directory is mounted at <path>/<entry> except those in
# --exclude (default: the dependency roots). What is never mounted simply stays the
# image's, so the disentangling is structural rather than a shadowing trick, and it uses
# nothing but plain bind mounts -- the one primitive every engine supports identically
# (verified on apple/container and Docker).
#
# Trade-off vs. the repo-root mode: the container gets the project directory only, not the
# repo root, so there is no .git and no sibling project. Lanes that need either (ruff and
# great-docs honoring .gitignore, the generate-* tasks reaching ../backend) keep the
# repo-root mode above.
#
# HOW TO NAME A BINARY IN A --cmd -- the rule follows from whether the lane mounts:
#   * Mounted (this helper): the workdir is the HOST tree, so anything that resolves
#     tooling relative to the cwd finds host-platform binaries. Invoke the binary by BARE
#     NAME (`ruff`, `great-docs`, `eslint`, `tsc`, `prettier`, `json2ts`) and let the
#     image's PATH resolve it -- backend/Dockerfile puts /app/.venv/bin there and
#     frontend/Dockerfile puts node_modules/.bin there. Do NOT use `npm run` or `uv run`,
#     and do NOT hardcode the image's WORKDIR inside a --cmd: that path belongs in the
#     Dockerfile, and --image-dir below is the one sanctioned place to name it.
#   * Not mounted (//:_container-run directly): the cwd is the image's own tree, so
#     `npm run <script>` is correct and preferred -- it reuses package.json's definition
#     instead of duplicating the command here.
container_dispatch() {
  [ -n "${usage_container:-}" ] || return 0
  if [ "${1:-}" != "--project" ]; then
    echo "container_dispatch: --project <name> must be the first argument" >&2
    exit 1
  fi
  # POSIX sh has no `local` and this is sourced into arbitrary task bodies, so fold the
  # parsed options into the positional parameters and unset the temporaries immediately,
  # rather than leaving variables behind in the caller's shell.
  _cd_project="$2"
  shift 2
  # Optional --image-dir/--exclude select the disentangled mode; anything else is passed
  # through to //:_container-run untouched.
  _cd_image_dir=""
  _cd_exclude="node_modules .venv"
  while [ $# -gt 0 ]; do
    case "$1" in
      --image-dir) _cd_image_dir="$2"; shift 2 ;;
      --exclude)   _cd_exclude="$2"; shift 2 ;;
      *) break ;;
    esac
  done

  if [ -z "$_cd_image_dir" ]; then
    # Repo-root mode: one mount, the whole repo at /src, workdir /src/<project>.
    set -- --workdir "/src/$_cd_project" "$@"
    unset _cd_project _cd_image_dir _cd_exclude
    exec mise run //:_container-run \
      --engine "${usage_engine:-auto}" \
      --bind-src "$(git -C "$PWD" rev-parse --show-toplevel)" \
      --bind-dst /src \
      --as-user \
      "$@"
  fi

  # Disentangled mode: one narrow mount per intended entry of the host project directory
  # (the cwd -- mise runs a task from the directory its config lives in). An entry is
  # skipped when git ignores it or it is named in --exclude, and whatever is skipped stays
  # the image's. Deferring to .gitignore keeps the rule self-maintaining: node_modules,
  # dist, caches and editor droppings drop out on their own, and a new one needs no change
  # here. --exclude then only has to name the correctness-critical dependency roots, so
  # the mechanism does not silently depend on .gitignore hygiene. Only top-level entries
  # are filtered -- a tracked directory is mounted whole, so gitignored *generated* files
  # inside it (src/types/models.ts, src/generated/referrals.ts) still come along, which
  # lint and typecheck require. Newline separated: //:_container-run splits on newlines
  # only, so a path containing spaces survives.
  _cd_ignored=$(ls -A "$PWD" | git -C "$PWD" check-ignore --stdin 2>/dev/null || true)
  _cd_mounts=""
  for _cd_entry in $(ls -A "$PWD"); do
    _cd_skip=""
    for _cd_ex in $_cd_exclude; do
      [ "$_cd_entry" = "$_cd_ex" ] && { _cd_skip=1; break; }
    done
    for _cd_ex in $_cd_ignored; do
      [ "$_cd_entry" = "$_cd_ex" ] && { _cd_skip=1; break; }
    done
    [ -n "$_cd_skip" ] && continue
    _cd_mounts="$_cd_mounts$PWD/$_cd_entry:$_cd_image_dir/$_cd_entry
"
  done
  set -- --mounts "$_cd_mounts" --workdir "$_cd_image_dir" "$@"
  unset _cd_project _cd_image_dir _cd_exclude _cd_mounts _cd_entry _cd_skip _cd_ex _cd_ignored
  exec mise run //:_container-run \
    --engine "${usage_engine:-auto}" \
    --as-user \
    "$@"
}
