# LangChain Implementation

This directory contains the LangChain-based implementation of the Tenant First Aid chatbot.

## Architecture Overview

The system uses a LangChain agent-based architecture with two main components:

1. **LangChainChatManager** (`langchain_chat_manager.py`): Orchestrates the agent and manages conversations
2. **RAG Tools** (`langchain_tools.py`): Two specialized tools for retrieving legal documents from Vertex AI

## Agent Flow

```
User Query → Agent → Tool Selection → RAG Retrieval → Response Generation → Stream to User
                ↓
          [retrieve_city_law]  (city-specific laws)
          [retrieve_state_law] (state-wide laws)
```

## Key Files

- `langchain_chat.py`: Main LangChain implementation
- `langchain_tools.py`: LangChain Agent tools
- `chat.py`: Original direct API implementation (to be deprecated)

## Usage

### Initializing the Chat Manager

```python
from tenantfirstaid.langchain_chat_manager import LangChainChatManager

manager = LangChainChatManager()
```

### Creating an Agent for a Session

```python
agent = manager.create_agent_for_session(city="Portland", state="or")
```

### Generating Responses

```python
# Non-streaming
response = agent.invoke({
    "input": "What is the notice period for eviction?",
    "chat_history": [],
    "city": "Portland",
    "state": "or"
})

# Streaming
for chunk in manager.generate_streaming_response(
    messages=[{"role": "user", "content": "What is the notice period?"}],
    city="Portland",
    state="or"
):
    print(chunk, end="", flush=True)
```

## RAG Tools

### retrieve_city_law

Retrieves city-specific housing laws using Vertex AI RAG.

**Parameters:**
- `query`: The legal question
- `city`: User's city (e.g., "portland")
- `state`: User's state (e.g., "or")

**Filter:** `city: ANY("{city}") AND state: ANY("{state}")`

### retrieve_state_law

Retrieves state-wide housing laws using Vertex AI RAG.

**Parameters:**
- `query`: The legal question
- `state`: User's state (e.g., "or")

**Filter:** `city: ANY("null") AND state: ANY("{state}")`

## Environment Variables

Required:
- `VERTEX_AI_DATASTORE`: Vertex AI datastore ID
- `GOOGLE_CLOUD_PROJECT`: GCP project ID
- `GOOGLE_CLOUD_LOCATION`: GCP region (default: us-central1)

Optional:
- `MODEL_NAME`: LLM model name (default: gemini-2.5-pro)
- `SHOW_MODEL_THINKING`: Enable Gemini thinking mode (default: false)
- `LANGSMITH_API_KEY`: Enable LangSmith tracing
- `LANGSMITH_PROJECT`: LangSmith project name

## Testing

```bash
# Run all LangChain tests
uv run pytest -k langchain

# Run specific test file
uv run pytest tests/test_langchain_chat.py

# Run with coverage
uv run pytest --cov=tenantfirstaid.langchain_chat tests/test_langchain_chat.py
```

## Migration from Direct API

The LangChain implementation provides several advantages over direct API calls:

1. **Standardized Architecture**: Uses industry-standard agent patterns
2. **Better Testability**: Easier to mock and test individual components
3. **Observability**: Built-in LangSmith tracing support
4. **Model Flexibility**: Easy to switch between different LLMs
5. **Tool Management**: Structured approach to RAG retrieval

### Key Differences

| Aspect | Direct API | LangChain |
|--------|-----------|-----------|
| Tool Integration | Manual tool config | Declarative `@tool` decorator |
| Message Format | Custom dict format | LangChain message types |
| Streaming | Direct generator | Agent streaming |
| Observability | Manual logging | LangSmith tracing |

## Common Issues

### Agent not using tools
**Symptom:** Agent responds without retrieving documents
**Fix:** Ensure tool docstrings clearly describe when to use each tool

### Slow responses
**Symptom:** Responses take longer than direct API
**Fix:** This is expected due to agent reasoning overhead (~100-200ms). Consider adjusting `max_iterations` if needed.

### Citation format issues
**Symptom:** Citations don't include HTML anchor tags
**Fix:** Ensure system prompt includes explicit citation format examples

## LangSmith Integration

### Enable Tracing

```bash
export LANGSMITH_API_KEY=your-api-key
export LANGSMITH_PROJECT=tenant-first-aid-dev
export LANGSMITH_TRACING=true
```
from [quickstart](https://docs.langchain.com/langsmith/trace-with-langchain#1-configure-your-environment)

### View Traces

Visit https://smith.langchain.com/ to see:
- Agent reasoning steps
- Tool calls and results
- Token usage
- Latency breakdown

## Future Enhancements

Potential improvements to consider:

1. **Memory Management**: Add conversation memory for better context
2. **Advanced RAG**: Implement multi-query retrieval or re-ranking
3. **Caching**: Cache frequent queries to reduce latency
4. **Streaming Optimization**: Optimize streaming for lower latency
5. **A/B Testing**: Use LangSmith to compare different models

## Resources

- [LangChain Documentation](https://python.langchain.com/)
- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [Vertex AI RAG Documentation](https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/rag-api)
