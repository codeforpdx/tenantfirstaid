# Pull Requests

Reference for commit messages, PR expectations, code review, and GitHub Actions security. Use the `/github` plugin for GitHub operations (issues, PRs, checks).

## Commit messages

Concise, imperative mood, small focused commits. Write like a humble experienced engineer — casual, no listicles, highlight non-obvious choices. No robot speak, marketing buzzwords, or vague fluff.

## PR expectations

Use the PR template (`.github/pull_request_template.md`). For frontend, backend, and backend/scripts changes:

- Add tests when needed
- Update documentation
- Run `make lint` and `make fmt`
- Full test suite passes

## PR reviews

Use `/review` for code review by default. Use `/ultrareview` only if the user explicitly asks for it — it is significantly more expensive but provides comprehensive multi-agent review with inline comments for specific issues and top-level comments for general observations.

Project-specific things to flag that ultrareview may not know without context:

- Style: `ruff format` + sorted imports + `make typecheck` passing
- Env vars consistent across GitHub Actions, `.env.example`, tests, and docs — no orphaned secrets
- Third-party GitHub Actions pinned to commit SHAs (see below)

## GitHub Actions security

Pin all third-party actions to commit SHAs to prevent supply chain attacks:

```yaml
# Good: SHA with version comment
uses: appleboy/scp-action@ff85246acaad7bdce478db94a363cd2bf7c90345 #v1.0.0

# Bad: floating tag
uses: appleboy/scp-action@v1.0.0
```

Exceptions: Astral (uv) actions may use fully qualified semver tags (e.g. `astral-sh/setup-uv@7.3.0`), and immutable tags are allowed.
