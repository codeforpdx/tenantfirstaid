# Source this (not execute) from a frontend/mise.toml host task before an npm script
# that shells out to the backend's uv. Splices the backend's mise-managed uv onto PATH,
# or exits with a clear error if it isn't installed yet.
uvbin=$(mise -C ../backend which uv || true)
if [ -z "$uvbin" ] || [ ! -x "$uvbin" ]; then
  echo "ERROR: Backend uv binary not found. Please run 'mise install' in the backend directory." >&2
  exit 1
fi
PATH="$(dirname "$uvbin"):$PATH"
