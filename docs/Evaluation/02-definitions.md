# Definitions

**RAG (Retrieval-Augmented Generation)**
A technique where the AI looks up relevant documents before writing a response, instead of relying solely on what it learned during training. In this project, "retrieval" means searching Oregon housing law texts; "generation" means composing the answer using those passages. This grounds responses in actual statutes rather than the model's general knowledge.

**Agent**
An AI that can do more than answer in one step — it can decide what tools to use, call them, and use the results to compose a final response. Tenant First Aid's chatbot is an agent: when a question comes in, it decides whether to search the legal corpus (the RAG retrieval tool), fetches relevant statutes, and then writes the response.

**System prompt**
A set of instructions given to the agent before any conversation starts. It defines the agent's role, tone, citation style, and legal guardrails ("you are a tenant rights assistant; always cite Oregon statutes; never give legal advice"). The user never sees it. In this codebase it lives in `tenantfirstaid/system_prompt.md`.

**Prompt** (in the context of evaluations)
The text sent to the AI judge telling it how to evaluate a response. Not to be confused with the system prompt above. An evaluator prompt is constructed from the rubric and the example data, and instructs the judge what criteria to apply and what format to return scores in.

**Rubric**
A plain-text document that defines the scoring criteria for one evaluator. It describes what earns a 1.0, 0.5, or 0.0 — for example, a legal correctness rubric says "1.0 = legally accurate; 0.0 = legally wrong or misleading." Rubrics live in `evaluate/evaluators/*.md` so lawyers and non-developers can edit them without touching Python code.

**Evaluator**
A piece of scoring logic that reads the chatbot's response to an example and assigns a score between 0.0 and 1.0. There are two kinds: *LLM-as-judge* evaluators use a second AI model guided by a rubric; *heuristic* evaluators use deterministic code (e.g. checking whether a citation link is well-formed). Each evaluator measures one dimension of quality — legal accuracy, tone, citation format, and so on.

**Example**
One test case. An example contains: the question a tenant asks, city/state context (because tenant law varies by jurisdiction), a reference conversation showing what a correct and well-toned response looks like, and a list of key legal facts the response must get right. Examples are the unit of work the evaluators score.

**Dataset**
The full collection of examples, stored locally in `evaluate/dataset-tenant-legal-qa-examples.jsonl` and uploaded to LangSmith for evaluation runs. The JSONL file in the git repository is the source of truth — the LangSmith copy is a working copy that is synced from it.

**Experiment**
One complete run of the dataset through the chatbot. Each experiment records which version of the code and system prompt was used, the chatbot's response to every example, and the evaluator scores. Experiments are compared side-by-side in the LangSmith UI to measure the impact of a code or prompt change.

**Deployment**
A version of the agent hosted in LangSmith Cloud, defined by `backend/langgraph.json`. A deployment is needed to run experiments from the LangSmith browser UI (so LangSmith can send test questions to a live endpoint) and to use Cloud Studio. Local development uses `langgraph dev` instead of a full deployment.

---

**Next**: [Data Flow](03-data-flow.md)
