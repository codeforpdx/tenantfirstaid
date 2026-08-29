# `--container` lanes resolve dependencies from the host tree

Handoff note for a session with a working container engine. Scratch file — delete or
relocate once resolved. Context: PR #387 (`fix-quick-start`).

## Problem

`scripts/container_dispatch.sh` bind-mounts the repo root at `/src` and sets the workdir
to `/src/<project>`. That mount carries two kinds of content with opposite requirements:

| Under the mount      | Should come from                          | Actually comes from |
| -------------------- | ----------------------------------------- | ------------------- |
| `src/`, config files | host (live edits — the point of mounting) | host ✅             |
| `node_modules/`      | image (pinned, reproducible tools)        | host ❌             |

`node_modules/` is _inside_ the project directory, so mounting the project necessarily
shadows it. The intent of `--container` — reproducible dev tooling — is violated for any
tool that resolves dependencies by filesystem location.

Affected: **`//frontend:lint` and `//frontend:typecheck`** ([frontend/mise.toml:87-91](frontend/mise.toml#L87-L91),
[:105-109](frontend/mise.toml#L105-L109)).

`frontend/Dockerfile` puts `node_modules/.bin` on `PATH`, so the _binary_ is the image's.
Everything it then loads is not:

- **eslint** reads `eslint.config.js` from the cwd (host tree). Flat config `import`s its
  plugins, and Node ESM resolves bare specifiers by walking up from the importing file →
  `/src/frontend/node_modules` = host. Result: image's eslint, host's rules, host's
  `typescript` (via `typescript-eslint`). Flat config removed the old
  `--resolve-plugins-relative-to` escape hatch.
- **tsc** resolves `@types` and library `.d.ts` by walking up from **each source file**,
  which is also in the mount. Pointing `-p` at the image's tsconfig would not help.

## Severity: real but not urgent

Not the same failure as the earlier `build`/`test` blocker. Nothing in the lint/typecheck
tree is native — `eslint`, `typescript`, `typescript-eslint`, `@typescript-eslint/*`,
`@eslint/*`, `eslint-plugin-react-hooks` contain zero `.node` files. (`@esbuild` and
`@rollup` are platform-specific, but only `build`/`test` use them, and those lanes were
already un-mounted for this reason.) `depends = ["install"]` installs the host tree from
the same `package-lock.json` the image's `npm ci` uses, so normally the two are identical.

Fails when: host install is stale/partial (eslint dies at config load with
`ERR_MODULE_NOT_FOUND`); someone `npm i`s without a lockfile change (image is reused —
reuse keys on `--cache-key-files` — so image binary meets host plugins, and eslint flat
config does cross-instance identity checks); or you are trying to reproduce a CI failure,
which is the entire purpose of the flag.

Confirmed _not_ a problem: `tsBuildInfoFile` points into the host `node_modules`, but
neither `composite` nor `incremental` is set, so `tsc --noEmit -p` never writes it.

## Why the backend doesn't have this bug

Same problem, already solved there — Python's dependency root is redirectable by env var:

- `UV_PROJECT_ENVIRONMENT=/app/.venv` ([backend/mise.toml:207-210](backend/mise.toml#L207-L210)
  and in `typecheck`/`check`) — comment already says "not the host's macOS
  `/src/backend/.venv`."
- `RUFF_CACHE_DIR=/tmp/ruff-cache` — same shape, keeps tool state out of the mount.
- `ruff` is a static binary with no dependency resolution at all.

One env var decouples "source from the mount, packages from the image." **Node has no
equivalent**: `NODE_PATH` is legacy-CJS-only and ignored by ESM; `typeRoots`/`paths` don't
cover imports resolved from source-file locations. So the fix cannot live in the command —
it has to be at the mount.

## Proposal (needs an engine to validate)

**Mask the nested `node_modules` with an inner mount that shadows the parent bind.**

Keep `-v <repo>:/src`, add a second mount at `/src/frontend/node_modules` seeded from the
image's own packages. Docker and Podman both let a deeper mount shadow a parent bind, and
an anonymous volume is initialized from the image's content at that path — which requires
the image to bake `node_modules` at that path, i.e. the frontend image's `WORKDIR` becomes
`/src/frontend`.

Generalized rule for `container_dispatch`: _a mount carries source only; every dependency
or tool-state directory under it needs either an out-of-tree redirect (backend's approach)
or an inner mount that shadows it._ The helper currently encodes only the first half.

### Must verify with a real engine

1. Does an anonymous volume at `/src/frontend/node_modules` seed from image content when
   `/src` is already a bind mount? (Expected yes on Docker/Podman; **unverified**.)
2. **apple/container support for nested/overlapping mounts** — it is one of the three
   supported engines and the most likely to not support this. If it doesn't, the helper
   needs an engine-conditional path, which may sink the approach.
3. Moving the frontend `WORKDIR` to `/src/frontend` must not break the `local`,
   `production-build`, or `production` stages, or `docker-compose.yml`.
4. Ownership: lanes run `--as-user`; confirm the volume is writable/readable as that uid.

### Alternatives if that fails

- **Drop the mount** for `lint`/`typecheck`, matching `build`/`test`. Correct and
  consistent, but image reuse in `//:_container-run` requires `--bind-src`
  ([mise.toml:238-243](mise.toml#L238-L243)), so every run becomes a full rebuild — and
  that helper's own comment notes apple/container re-transfers the whole build context even
  when layers are cached. Painful for tight edit loops.
- **eslint only**: `eslint --config /workspace/frontend/eslint.config.js /src/frontend/src`
  — plugins resolve from the image, source stays live, mount preserved. Does not
  generalize to tsc (see above).
- **Document and accept**: given zero native deps and a lockfile-pinned host install, the
  residual risk is version skew. An inline comment stating the limitation would close the
  finding honestly, at the cost of `--container` not fully meaning what it says.

## Note on verification state

None of the container work on this branch has been executed against a real engine — no
docker/podman/apple `container` in the authoring sandbox. All checks were stub-`mise` argv
assertions, which prove flag plumbing only. Two other untested behavior changes worth a
smoke test on your side:

- The four `docs*` tasks switched from mounting `backend/` to mounting the repo root, with
  `PYTHONPATH` and `great-docs`' absolute `.qmd` paths adjusted to `/src/backend`. If
  `great-docs` infers `project_root` by walking upward, it may now pick `/src`.
- `backend:fmt --write` now sees the repo's real `.git` where it previously didn't.
