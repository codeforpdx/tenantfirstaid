# Source this (not execute) from a project mise.toml task's `run` body, then call
# `container_dispatch [--bind-src <dir>] --image ... --context ... --cache-key-files "..."
# --cmd "..." [extra //:_container-run flags]`. When --container was passed to the task,
# this execs `mise run //:_container-run` with the engine/bind-mount/as-user options that
# are identical across (almost) every containerized task in this repo, appending whatever
# flags the caller passed; it never returns in that case. Without --container it returns 0
# so the host command below it runs instead.
#
# Defaults --bind-src to the repo root; pass a leading --bind-src to override it (backend's
# `fmt --write` and docs* tasks bind-mount backend/ instead, since their commands assume
# /src is the backend directory). One task (frontend's `check`) bind-mounts nothing at all
# and skips this helper, calling //:_container-run directly.
container_dispatch() {
  [ -n "${usage_container:-}" ] || return 0
  bind_src="$(git -C "$PWD" rev-parse --show-toplevel)"
  if [ "${1:-}" = "--bind-src" ]; then
    bind_src="$2"
    shift 2
  fi
  exec mise run //:_container-run \
    --engine "${usage_engine:-auto}" \
    --bind-src "$bind_src" --bind-dst /src --as-user \
    "$@"
}
