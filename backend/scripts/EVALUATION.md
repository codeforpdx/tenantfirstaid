# Automated Evaluation with LangSmith

## Overview

Tenant First Aid uses LangSmith for automated quality evaluation of legal advice responses. This replaces the previous manual conversation generation workflow (`backend/scripts/generate_conversation`).

## Benefits Over Manual Evaluation

| Aspect | Manual (`generate_conversation`) | Automated (LangSmith) |
|--------|----------------------------------|----------------------|
| **Speed** | Hours to days | Minutes |
| **Scale** | 10-50 scenarios/session | 100s-1000s of scenarios |
| **Metrics** | Subjective human review | Quantitative scores (0-1) |
| **Consistency** | Varies by reviewer | Consistent LLM-as-judge |
| **Regression Detection** | Manual comparison | Automatic alerts |
| **CI/CD** | Not integrated | Runs on every PR |
| **Cost** | $50-100/hr (human time) | $5-10 (LLM judge API) |

## Running Evaluations

### One-Time Setup

1. Install the evaluator dependency. The chatbot uses `langchain-google-genai`, but the LLM-as-judge evaluators use `init_chat_model()` which resolves Gemini models to `ChatVertexAI` under the hood:

```bash
cd backend
uv add --group dev langchain-google-vertexai
```

2. Create the LangSmith dataset from existing test scenarios:

```bash
uv run python scripts/create_langsmith_dataset.py
```

This uploads test scenarios from `scripts/generate_conversation/tenant_questions_facts_full.csv` to LangSmith.

### Local Development

Run evaluation on the full dataset:

```bash
cd backend
uv run python scripts/run_langsmith_evaluation.py
```

Run a specific experiment:

```bash
uv run python scripts/run_langsmith_evaluation.py \
  --dataset "tenant-legal-qa-scenarios" \
  --experiment "my-experiment" \
  --num-repetitions 1
```

### CI/CD

Because CI runs on PRs from forked repos, those jobs do not have access to repo vars/secrets (i.e. API keys).  Therefore PRs cannot automatically run LangSmith evaluations.

## Metrics Explained

### Citation Accuracy (0.0-1.0) :construction:
Evaluates if responses include proper citations to Oregon laws.
- **1.0**: Proper ORS citations with HTML anchor tags
- **0.5**: Citations present but formatting issues
- **0.0**: Missing or incorrect citations

**Example passing response:**
```html
According to <a href="https://oregon.public.law/statutes/ors_90.427" target="_blank">ORS 90.427</a>,
landlords must provide 30 days notice for no-cause eviction.
```

### Legal Correctness (0.0-1.0)
Evaluates if legal advice is accurate based on Oregon tenant law.
- **1.0**: Legally accurate advice
- **0.5**: Partially accurate or incomplete
- **0.0**: Legally incorrect or misleading

### Completeness (0.0-1.0) :construction:
Evaluates if response fully addresses the user's question.
- **1.0**: Comprehensive answer with context
- **0.5**: Partial answer
- **0.0**: Off-topic or unhelpful

### Tone (0.0-1.0)
Evaluates if tone is appropriate for legal advice.
- **1.0**: Professional, accessible, empathetic
- **0.5**: Tone issues (too formal/casual)
- **0.0**: Inappropriate tone

**Anti-patterns:**
- Starting with "As a legal expert..."
- Overly technical jargon
- Dismissive or condescending language

### Citation Format (Binary) :construction:
Checks HTML anchor tag format compliance.
- **Pass**: Uses `<a href="..." target="_blank">ORS X.XXX</a>`
- **Fail**: Missing anchor tags or incorrect format

### Tool Usage (Binary) :construction:
Checks if agent used RAG retrieval appropriately.
- **Pass**: Used `retrieve_city_law` or `retrieve_state_law`
- **Fail**: No retrieval tools used for legal question

### Performance :construction:
Tracks latency and token usage.
- **Good**: < 5 seconds
- **Acceptable**: 5-10 seconds
- **Poor**: > 10 seconds

## Adding New Test Scenarios

1. Edit the CSV file:
```bash
# Edit backend/scripts/generate_conversation/tenant_questions_facts_full.csv
# Add new row with: first_question, facts, city, state
```

2. Re-upload to LangSmith:
```bash
cd backend/scripts
uv run python create_langsmith_dataset.py --dataset-name tenant-legal-qa-scenarios [--overwrite] [--limit-examples 4]
```

## Viewing Results

### LangSmith Dashboard
https://smith.langchain.com/

- **Experiments**: Compare runs side-by-side
- **Datasets**: Manage test scenarios
- **Traces**: Debug individual responses
- **Metrics**: Track quality over time

## Dataset Structure

- **Inputs**: query, city, state (what the model receives)
- **Reference Outputs**: facts, reference_conversation (ground truth)

## Evaluator Run Structure
- Inputs (to the evaluator, e.g. LLM-as-a-Judge)
  - **inputs** - `dataset.inputs`
  - **outputs**
    - `Model-Under-Test Output`: what the chatbot responded with
    - `Model-Under-Test Reasoning`: what the chatbot was thinking. Optionally captured for debugging (`SHOW_MODEL_THINKING` env var)
    - `Model-Under-Test System Prompt`: what the chatbot was given as instructions
  - **reference_outputs** - `dataset.reference outputs`

### Example Workflow

1. **Make code changes** to improve citation accuracy
2. **Run evaluation locally**:
   ```bash
   uv run python scripts/run_langsmith_evaluation.py --experiment "improve-citations"
   ```
3. **View results** in LangSmith dashboard
4. **Compare** with baseline experiment
5. **Iterate** based on metrics

## A/B Testing Different Models

Compare Gemini 2.5 Pro vs Claude 3.5 Sonnet:

```bash
# Baseline: Gemini 2.5 Pro
uv run python scripts/run_langsmith_evaluation.py \
  --experiment "baseline-gemini-2.5-pro"

# Update MODEL_NAME environment variable to claude-3-5-sonnet-20241022
# and LangChainChatManager to use ChatAnthropic

# Experiment: Claude 3.5 Sonnet
uv run python scripts/run_langsmith_evaluation.py \
  --experiment "experiment-claude-3.5-sonnet"

# View side-by-side comparison in LangSmith dashboard
```

## Troubleshooting

### Evaluation fails with "Dataset not found"
Run `uv run python scripts/create_langsmith_dataset.py` to create the dataset.

### Scores seem inaccurate
LLM-as-judge evaluators can have biases. Review specific examples in LangSmith dashboard and refine evaluator prompts in `scripts/langsmith_evaluators.py` if needed.

### Evaluation too slow
- Reduce `max_concurrency` in `run_langsmith_evaluation.py`
- Reduce the dataset size in LangSmith to evaluate a subset
- Consider running full evaluation only before releases

### LANGSMITH_API_KEY not set
1. Create account at https://smith.langchain.com/
2. Generate API key from settings
3. Set environment variable in [.env](../.env)
   ```bash
  LANGSMITH_API_KEY=your-api-key
   ```

## Environment Variables

```bash
# Required for evaluation
GOOGLE_CLOUD_PROJECT=your-project
GOOGLE_CLOUD_LOCATION=us-central1
VERTEX_AI_DATASTORE=projects/.../datastores/...
LANGSMITH_API_KEY=your-api-key

# Optional
LANGSMITH_PROJECT=tenant-first-aid-dev  # Project name in LangSmith
LANGSMITH_TRACING=true
LANGCHAIN_TRACING_V2=true               # Enable detailed tracing
MODEL_NAME=gemini-2.5-pro               # Model to evaluate
SHOW_MODEL_THINKING=true                # capture reasoning in LangSmith Evaluator Run view
```

## Best Practices

1. **Run evaluations before major releases** to catch regressions
2. **Track metrics over time** to monitor quality trends
3. **Add new test scenarios** when bugs are found in production
4. **Review failed evaluations** to understand edge cases
5. **Use A/B testing** when considering model changes
6. **Set quality thresholds** in CI/CD to prevent quality degradation

## Questions or Issues?
Contact the maintainers or open an issue on GitHub.
