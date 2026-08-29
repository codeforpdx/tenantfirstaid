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
# HOW TO NAME A BINARY IN A --cmd -- the rule follows from whether the lane mounts:
#   * Mounted (this helper): the workdir is the HOST tree, so anything that resolves
#     tooling relative to the cwd finds host-platform binaries. Invoke the binary by BARE
#     NAME (`ruff`, `great-docs`, `eslint`, `tsc`, `prettier`, `json2ts`) and let the
#     image's PATH resolve it -- backend/Dockerfile puts /app/.venv/bin there and
#     frontend/Dockerfile puts node_modules/.bin there. Do NOT use `npm run` or `uv run`,
#     and do NOT hardcode the image's WORKDIR: that path belongs in the Dockerfile only.
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
  # project name into the positional parameters and unset the one temporary immediately,
  # rather than leaving a variable behind in the caller's shell.
  _cd_workdir="/src/$2"
  shift 2
  set -- --workdir "$_cd_workdir" "$@"
  unset _cd_workdir
  exec mise run //:_container-run \
    --engine "${usage_engine:-auto}" \
    --bind-src "$(git -C "$PWD" rev-parse --show-toplevel)" \
    --bind-dst /src \
    --as-user \
    "$@"
}
