# Source this (not execute) from a project mise.toml task's `run` body, then call
# `container_dispatch --image ... --context ... --cache-key-files "..." --cmd "..." [extra
# //:_container-run flags]`. When --container was passed to the task, this execs
# `mise run //:_container-run` with the engine/bind-mount/as-user options that are
# identical across (almost) every containerized task in this repo, appending whatever
# flags the caller passed; it never returns in that case. Without --container it
# returns 0 so the host command below it runs instead.
#
# Two tasks bind-mount something other than the repo root (backend's `fmt --write`
# mounts only backend/) and skip this helper, calling //:_container-run directly.
container_dispatch() {
  [ -n "${usage_container:-}" ] || return 0
  exec mise run //:_container-run \
    --engine "${usage_engine:-auto}" \
    --bind-src "$(git -C "$PWD" rev-parse --show-toplevel)" --bind-dst /src --as-user \
    "$@"
}
