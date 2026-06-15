# Solution Plan — Rate-limit the `/api/query` endpoint

Branch: `feature-rate-limit-api-query` (local; see "Branch" note below)

## Understand (the problem in my own words)

Every `POST /api/query` fans out to Vertex AI RAG retrieval + a Gemini LLM call —
the single most expensive operation in the app. Right now that endpoint has **no
rate limit**, so a script (or bot) can hammer it as fast as it likes and run up
Google Cloud cost / starve real tenants of availability. The `flask_limiter`
machinery is already wired into the app, but the only `@limiter.limit(...)` in the
codebase is on `/api/feedback`. `/api/query` was simply never given a limit.

**What should happen instead:** `/api/query` should reject a client that exceeds a
sane per-IP request budget with HTTP `429 Too Many Requests`, exactly the way
`/api/feedback` already does.

Out of scope (per the issue): user auth / login. This is an anonymous public
legal-aid tool; we want abuse protection, not identity. Turnstile/hCaptcha is an
optional follow-up only if the rate limiter proves insufficient.

## Reproduction (confirmed twice)

Fired a burst at each endpoint against the real Flask app (LLM + email mocked):

| Endpoint | Requests | Result | 429s |
|---|---|---|---|
| `/api/query` | 20 | `{200: 20}` | **0** ← unprotected (bug) |
| `/api/feedback` | 5 | `{200: 3, 429: 2}` | 2 ← limiter works here |

Bug reproduced in **2/2 trials**. Repro script: `/tmp/repro_rate_limit.py`.

## 1. Root cause

In [backend/tenantfirstaid/app.py](backend/tenantfirstaid/app.py):

- The `Limiter` is created at [app.py:20-24](backend/tenantfirstaid/app.py#L20-L24)
  **without any `default_limits`**, so no global limit applies to any route.
- `/api/feedback` is wrapped by a `@limiter.limit("3 per minute")` decorator at
  [app.py:58-68](backend/tenantfirstaid/app.py#L58-L68).
- `/api/query` is registered at [app.py:55](backend/tenantfirstaid/app.py#L55) as
  a bare class-based view:
  ```python
  app.add_url_rule("/api/query", view_func=ChatView.as_view("chat"), methods=["POST"])
  ```
  No `limiter.limit(...)` is ever attached to it. With no per-route limit and no
  default limit, the costly endpoint accepts unlimited traffic.

The behavior traces directly to the *absence* of a limit on the `chat` endpoint —
not to a misconfiguration elsewhere. CORS and the limiter exist; the limiter just
isn't pointed at `/api/query`.

## 2. Proposed fix (high level)

Attach a `flask_limiter` limit to the `/api/query` route in `app.py`, mirroring the
existing `/api/feedback` pattern. Because `ChatView` is a class-based view, I will
apply the limit to the object returned by `ChatView.as_view("chat")` before
registering it:

```python
chat_view = limiter.limit("10 per minute")(ChatView.as_view("chat"))
app.add_url_rule("/api/query", view_func=chat_view, methods=["POST"])
```

(Equivalently, set `decorators = [limiter.limit("10 per minute")]` on `ChatView`.)

- Limit value: a per-IP budget generous enough for a real back-and-forth chat
  (a human turn every few seconds) but low enough to stop scripted abuse. I'll
  propose `10 per minute` and confirm the exact number with mentors, optionally
  reading it from an env var so it's tunable without a redeploy.
- Keep the limit per-IP via the existing `get_remote_address` key function. Note
  for the PR/Deployment discussion: behind the Digital Ocean proxy the limiter
  must see the real client IP (`X-Forwarded-For` / `ProxyFix`), otherwise all
  traffic shares one bucket — I'll verify how the app is fronted in production.

## 3. Files I expect to touch

- [backend/tenantfirstaid/app.py](backend/tenantfirstaid/app.py) — attach the
  limit to the `/api/query` route (primary change).
- [backend/tests/test_app.py](backend/tests/test_app.py) — add a test asserting
  `/api/query` returns `429` after the limit is exceeded.
- [backend/.env.example](backend/.env.example) — only if the limit is made
  configurable via an env var (document the new variable).
- [Architecture.md](Architecture.md) — only if the endpoint protections section
  needs updating (per the PR template's documentation checkbox).

## 4. How I'll verify it works

**Automated tests (pytest, the project's required test type):**
- Add `test_query_rate_limiting_returns_429` to `TestQueryRoute` in
  `test_app.py`, modeled on the existing `test_rate_limiting_returns_429` for
  feedback: send N+1 mocked `/api/query` requests and assert the last is `429`.
- Add a test asserting a request *within* the limit still returns `200`, so the
  limit isn't so tight it breaks normal chat.
- The existing `reset_rate_limiter` autouse fixture keeps trials isolated.

**Regression / no-collateral-damage:**
- `make --keep-going check` in `backend/` (ruff format, ruff lint, ty typecheck,
  pytest) must stay green.
- Re-run `/tmp/repro_rate_limit.py`: after the fix `/api/query` should show
  `429`s once the burst exceeds the limit (the inverse of today's result), while
  `/api/feedback` is unchanged.

## Match (similar pattern already in the codebase)

The fix is a near-copy of the existing feedback limit:
- `@limiter.limit("3 per minute")` on `feedback_route`
  ([app.py:58-68](backend/tenantfirstaid/app.py#L58-L68)).
- Its test `TestFeedbackRoute::test_rate_limiting_returns_429`
  ([test_app.py:91-101](backend/tests/test_app.py#L91-L101)) is the template for
  the new `/api/query` test.

## Plan (step by step)

1. Decide the per-IP limit value (default `10/min`, confirm with mentors); make it
   env-configurable if desired.
2. Wrap `ChatView.as_view("chat")` with `limiter.limit(...)` in `app.py`.
3. Add the 429 + within-limit tests to `test_app.py`.
4. Run `make --keep-going check`; re-run the repro script to confirm inversion.
5. (Optional follow-up, only if needed) Cloudflare Turnstile / hCaptcha token
   verified server-side.

## Implement

_Placeholder — implemented in Phase III on branch `feature-rate-limit-api-query`._
PR link: _TBD_

## Review (against project conventions)

- No `CONTRIBUTING.md` exists in the repo. Conventions come from
  [.github/pull_request_template.md](.github/pull_request_template.md): I'll fill
  in PR type (**Bug Fix**), Description, link the issue (`Closes #<n>`), QA
  instructions, check the "Added/updated tests? → Yes" box, and the Architecture
  doc checkbox if applicable.
- Branch naming follows the observed `feature-*` / `issue-<n>/desc` convention.
- Per `.claude/CLAUDE.md` style: comments are full sentences ending in a period.
- Pre-PR checks come from the README / `pr-check.yml`: ruff format, ruff lint, ty,
  pytest must all pass.

## Evaluate

The project requires automated tests (pytest in CI via `pr-check.yml`). The fix is
considered verified when: the new `/api/query` 429 test passes, the within-limit
200 test passes, the full `make check` suite is green, and the repro script shows
`/api/query` now returns 429s under burst.

---

### Environment-setup notes / errors encountered (documented per request)

1. **`/api/query` import needs GCP creds; placeholder `.env` path breaks it.**
   The `.env` copied from `.env.example` sets
   `GOOGLE_APPLICATION_CREDENTIALS=/home/<USERNAME>/...` (a placeholder). Real
   credentials require Google project access granted via the project's Discord —
   not available in this environment. *Workaround (matches CI's forked-repo path
   in `pr-check.yml`):* set fake env vars
   `GOOGLE_CLOUD_PROJECT`, `GOOGLE_APPLICATION_CREDENTIALS=/tmp/fake-google-credentials.json`,
   `VERTEX_AI_DATASTORE_LAWS`, `GOOGLE_CLOUD_LOCATION` and run tests with
   `-m "not require_repo_secrets"`. Tests mock the LLM, so a non-existent creds
   path is fine for the lazy auth check.

2. **`socksio` missing → httpx fails importing `evaluate.run_langsmith_evaluation`.**
   The sandbox sets `ALL_PROXY=socks5h://localhost:54568`, but the `socksio`
   package isn't installed, so httpx raises `ImportError: Using SOCKS proxy, but
   the 'socksio' package is not installed` when the LangSmith client is built.
   This import is pulled in by the autouse `_no_eval_history_writes` fixture in
   `tests/conftest.py`, so it broke *every* test (surfacing confusingly as
   `AttributeError: module 'evaluate' has no attribute 'run_langsmith_evaluation'`).
   *Workaround:* `unset ALL_PROXY all_proxy GRPC_PROXY grpc_proxy FTP_PROXY ftp_proxy RSYNC_PROXY`
   before running pytest. After this, all 8 `test_app.py` tests pass.

3. **`git push` blocked — no GitHub credentials in the sandbox.**
   `git push` returns `could not read Username for 'https://github.com': Device
   not configured`; there is no `gh` CLI, no `GH_TOKEN`/`GITHUB_TOKEN`, and no
   keychain credential reachable non-interactively. The branch
   `feature-rate-limit-api-query` exists locally and is ready. **Action needed
   from you:** run `git push -u origin feature-rate-limit-api-query` in an
   authenticated terminal.
