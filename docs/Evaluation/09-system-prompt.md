# Editing the System Prompt

> **Audience**: legal contributors (via Cloud Studio) and content/frontend contributors (via editor + `langgraph dev`).

The system prompt lives in `backend/tenantfirstaid/system_prompt.md`. It controls the chatbot's personality, tone, citation style, and legal guardrails — everything from "always cite Oregon statutes" to how empathetically it responds.

Anyone can edit it. No Python knowledge required.

## Two ways to edit

### Via Cloud Studio (legal contributors — browser only)

The Configuration panel in Studio lets you test changes immediately without editing any files. Best for iterating on phrasing.

1. Open [Cloud Studio](04-cloud-studio.md).
2. Find the **Configuration** panel (sidebar or top bar). You'll see a text field labeled **system_prompt**.
3. Edit the prompt — changes take effect on your next message, no restart needed.
4. Test with several questions. Each thread remembers your config so you can compare.
5. When satisfied, copy the text and paste it into `system_prompt.md`. Commit and push.

> The Configuration panel is per-conversation. Starting a new thread reverts to the default from `system_prompt.md`. Your changes aren't permanent until you commit the file.

### Via editor + `langgraph dev` (content/frontend contributors)

Edit the file directly and reload Studio.

1. Open `backend/tenantfirstaid/system_prompt.md` in your editor.
2. Make your changes.
3. Restart `langgraph dev` (`Ctrl+C`, then `uv run langgraph dev` again) — it reloads the prompt file on startup.
4. Test in Studio.
5. Open a pull request with the edited file.

## Placeholders

The file uses two runtime placeholders — keep them exactly as written:

| Placeholder | Current value |
|-------------|---------------|
| `{RESPONSE_WORD_LIMIT}` | 350 |
| `{OREGON_LAW_CENTER_PHONE_NUMBER}` | 888-585-9638 |

Do **not** add other `{...}` placeholders — Python's `str.format()` will break on stray curly braces.

## After editing

Once you have a version you're happy with:

1. Copy the text into `backend/tenantfirstaid/system_prompt.md` (keeping the two placeholders above).
2. Commit and push.
3. Ask a backend contributor to run an evaluation to verify the change didn't break anything across the full example suite.

---

**Next**: [Editing Evaluator Rubrics](10-evaluator-rubrics.md)
