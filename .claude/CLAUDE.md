# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository overview

Tenant First Aid is a chatbot for Oregon housing/eviction legal information. Flask backend + React frontend monorepo, deployed on Digital Ocean.

- **Architecture docs**: [Architecture.md](../Architecture.md) — RAG pipeline, endpoints, session management, frontend structure
- **Deployment docs**: [Deployment.md](../Deployment.md) — CI/CD, secrets, infrastructure
- **PR template**: [.github/pull_request_template.md](../.github/pull_request_template.md)
- **Dev commands**: `backend/Makefile`

### Key architecture

- **Backend** (`backend/`): Flask API with LangChain agent orchestration. The agent uses Vertex AI RAG to retrieve Oregon housing law documents and Google Gemini as the LLM. Key files: `langchain_chat_manager.py` (agent orchestration), `langchain_tools.py` (RAG retriever + letter tools), `schema.py` (Pydantic response chunk types shared with frontend).
- **Frontend** (`frontend/`): React 19 + TypeScript + Vite + Tailwind CSS 4. Uses `@langchain/core` message types (`HumanMessage`/`AIMessage`) directly for chat state. Streaming via native `ReadableStream`.
- **Type bridge**: Frontend TypeScript types in `src/types/` are auto-generated from backend Pydantic models via `generate-types` and gitignored. Must regenerate before building or type-checking.

## Style notes

- Write comments as full sentences and end them with a period.

## Skills

Load these on demand -- don't include their content in every response, just invoke them when the task calls for it.

| Skill | When to use |
|---|---|
| `/onboarding` | Setting up the repo for the first time or helping a new contributor |
| `/backend` | Working on backend code (commands, env vars, Docker) |
| `/frontend` | Working on frontend code (commands, type generation, Docker) |
| `/corpus-dataset` | Adding, modifying, or reviewing `.txt` law files in `backend/scripts/documents/` (includes ASCII enforcement rules) |
| `/evaluation` | Running, analyzing, or improving LangSmith evaluations |
| `/pr` | Writing commit messages, opening PRs, or reviewing code |
