# Typical Workflows

## "I want to check quality before a release" (backend contributors)

```mermaid
flowchart LR
    A["Run evaluation<br>run_langsmith_evaluation.py"] --> B["Review scores<br>in LangSmith UI"]
    B --> C{Passing?}
    C -- Yes --> D["Ship it"]
    C -- No --> E["Investigate failing<br>examples in UI"]
    E --> F["Fix chatbot code<br>or system prompt"]
    F --> A
```

## "I found a chatbot mistake and want to add a test for it"

**Content/frontend contributors**: follow [Contributing Test Examples](08-contributing-examples.md) to submit the example, then ask a backend contributor to run an evaluation.

**Backend contributors**:

```mermaid
flowchart LR
    A["Write the example<br>(question + reference answer)"]
    B["Append to JSONL<br>example append"]
    C["Push to LangSmith<br>dataset push"]
    D["Run evaluation<br>to confirm it fails"]
    E["Fix the chatbot"]
    F["Run evaluation<br>to confirm it passes"]
    G["Commit JSONL + code fix"]

    A --> B --> C --> D --> E --> F --> G
```

## "I want to improve a reference answer using the browser editor" (all audiences)

```mermaid
flowchart LR
    A["Edit in<br>LangSmith UI"] --> B["Notify backend contributor<br>on Discord"]
    B --> C["Backend: dataset pull<br>+ review diff in git"]
    C --> D["Commit<br>updated JSONL"]
```

## "I want to iterate on the system prompt"

**Legal contributors (browser)**: See [Cloud Studio](04-cloud-studio.md) and [Editing the System Prompt](09-system-prompt.md).

**Content/frontend contributors (local)**: See [Local Studio](07-local-studio.md) and [Editing the System Prompt](09-system-prompt.md).

---

**Next**: [Troubleshooting](17-troubleshooting.md)
