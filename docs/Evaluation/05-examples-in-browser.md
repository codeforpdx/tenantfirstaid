# Adding or Editing Examples in the Browser

> **Audience**: legal contributors using the LangSmith browser UI. No terminal required.
>
> If you're a frontend or content contributor working locally, see [Contributing Test Examples](08-contributing-examples.md) instead.

The LangSmith browser editor lets you add new test examples, refine reference answers, or reword questions directly in your browser.

## What is an example?

One test case. It contains:
- **The question** — exactly what a tenant might ask
- **City/state context** — because tenant law varies by jurisdiction
- **Reference answer** — what a correct, well-toned response looks like
- **Key facts** — the legal facts the response must get right

The full collection of examples is the *dataset*. When you run an evaluation, LangSmith scores the chatbot's response to each example.

## Editing an existing example

1. Go to **LangSmith → Datasets → `tenant-legal-qa-scenarios`**.
2. Click on the example you want to edit.
3. Edit the `inputs` (question, city, state) or `outputs` (facts, reference conversation) directly.
4. Save.

**Important**: edits made in the browser stay in the cloud copy only. A backend contributor must pull the changes and commit them before other contributors see them. Mention in `#tenantfirstaid-general` on Discord when you've made changes so someone knows to pull.

## Adding a new example

1. Go to **LangSmith → Datasets → `tenant-legal-qa-scenarios`**.
2. Click **+ Add Example**.
3. Fill in the `inputs` and `outputs`. The format:

```json
{
  "inputs": {
    "query": "My landlord hasn't fixed my heat for two weeks — what can I do?",
    "city": null,
    "state": "OR"
  },
  "outputs": {
    "facts": [
      "Landlord has failed to repair heating for 14 days",
      "ORS 90.365 allows rent reduction after 7 days written notice"
    ],
    "reference_conversation": [
      { "role": "human", "content": "My landlord hasn't fixed my heat for two weeks — what can I do?" },
      { "role": "ai", "content": "Under ORS 90.365, ..." }
    ]
  }
}
```

4. Save. The new example won't have a `scenario_id` yet — a backend contributor will assign one when they pull and commit.

## What makes a good reference answer?

The reference conversation is what the AI judge measures the chatbot's response against. A strong reference answer:

- **Cites specific statutes** — include the ORS or city code number (e.g., `ORS 90.365`)
- **States the tenant's rights plainly** — avoid dense legal jargon
- **Includes concrete next steps** — what should the tenant actually do?
- **Gets the tone right** — empathetic and accessible, not condescending or overly formal
- **Doesn't give legal advice** — say "you may have the right to..." not "you should..."

## What makes a good set of key facts?

The `facts` list is used by the legal correctness evaluator. Each fact should be:

- Verifiable against Oregon housing law
- A single, specific claim (not a vague summary)
- Phrased as a statement, not a question

Example of a **good** fact: `"ORS 90.365 allows rent reduction after 7 days written notice of the repair needed"`

Example of a **weak** fact: `"Tenant has some rights about repairs"`

## After you're done

Post in `#tenantfirstaid-general` on Discord:
> "Added/edited example in `tenant-legal-qa-scenarios` — [brief description]. Needs pull + commit."

A backend contributor will run `dataset pull`, review the diff, and commit the changes to the repo.

---

**Next steps:**
- Run a scored experiment to see how the chatbot performs on the new example → [Bound Evaluators](06-bound-evaluators.md)
- View past results → [Viewing & Comparing Results](11-viewing-results.md)
