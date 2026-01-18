# LangChain Migration Guide

## Overview
This document describes the migration from direct Google Gemini API calls to LangChain 1.0.8+ agent-based architecture with LangSmith evaluation capabilities.

## What Changed

### Backend Architecture
- **Before**: Direct `google-genai` SDK calls with manual tool integration
- **After**: LangChain agent-based architecture with standardized patterns

### Evaluation Workflow
- **Before**: Manual conversation generation and human review (`backend/scripts/generate_conversation`)
- **After**: Automated LangSmith evaluation with quantitative metrics

## Migration Phases

### Phase 1: Parallel Implementation (Week 1-2)
- [x] Add LangChain dependencies to pyproject.toml
- [ ] Implement LangChainChatManager alongside existing ChatManager
- [ ] Create unit tests for new implementation
- [ ] Set up development environment with LangSmith tracing

### Phase 2: Testing & Validation (Week 2-3)
- [ ] Run integration tests with real Vertex AI
- [ ] Perform regression testing (compare responses side-by-side)
- [ ] Validate streaming performance
- [ ] Test location-based filtering accuracy

### Phase 3: Gradual Rollout (Week 3-4)
- [ ] Deploy to staging environment
- [ ] Enable LangSmith observability
- [ ] Run A/B comparison (10% traffic to LangChain)
- [ ] Monitor error rates and response quality

### Phase 4: Full Migration (Week 4)
- [ ] Route 100% traffic to LangChain implementation
- [ ] Remove old ChatManager code
- [ ] Update all documentation
- [ ] Set up production LangSmith monitoring

## Rollback Plan
If issues arise, immediately revert to previous implementation by:
1. Update `chat.py` to use `ChatManager` instead of `LangChainChatManager`
2. Redeploy backend service
3. No database/session changes required (session format unchanged)

## Success Metrics
- Response latency < 2s for first chunk (same as current)
- Citation accuracy ≥ 95% (maintain current quality)
- Zero increase in error rate
- LangSmith traces show proper tool usage

## Known Differences
- Agent may use tools differently than current dual-tool approach
- Tool selection is now autonomous rather than hardcoded
- Additional latency (~100-200ms) from agent reasoning overhead

## Troubleshooting

### Issue: Agent not using retrieval tools
**Cause:** Tool descriptions may be unclear
**Fix:** Update tool docstrings to be more explicit about when to use each tool

### Issue: Streaming slower than current implementation
**Cause:** Agent execution overhead
**Fix:** Consider optimizing agent configuration or adjusting streaming strategy

### Issue: Citations not formatted correctly
**Cause:** System prompt may need adjustment for LangChain agent
**Fix:** Enhance system prompt with explicit citation examples

## Testing the Migration

### Running Tests
```bash
cd backend

# Run all LangChain tests
uv run pytest -k langchain

# Run specific test file
uv run pytest tests/test_langchain_chat.py

# Run with coverage
make test TEST_OPTIONS="--cov tenantfirstaid.langchain_chat --cov-report html"
```

### Manual Testing
```bash
# Start development server with LangChain
export USE_LANGCHAIN=true
uv run flask --app tenantfirstaid.app run
```

## Environment Variables

### Required for LangChain
```bash
# Existing variables (already set)
GOOGLE_CLOUD_PROJECT=your-project
GOOGLE_CLOUD_LOCATION=us-central1
VERTEX_AI_DATASTORE=projects/.../datastores/...
MODEL_NAME=gemini-2.5-pro

# New for LangSmith (optional but recommended)
LANGSMITH_API_KEY=your-api-key
LANGSMITH_PROJECT=tenant-first-aid-dev
LANGSMITH_TRACING_V2=true  # Enable tracing
```

## Documentation Updates
- [x] Update Architecture.md with LangChain architecture
- [ ] Add LangSmith evaluation documentation
- [ ] Update CLAUDE.md with new development workflow
- [ ] Document environment variables

## Benefits

### Immediate
- Standardized architecture using industry-standard patterns
- Better code maintainability and testability
- Automated quality evaluation replaces manual review

### Future Enablement
- LangSmith observability for production debugging
- Easy model switching (Gemini → Claude → GPT-4)
- Access to LangChain ecosystem (advanced RAG, memory, etc.)
- Continuous quality monitoring and regression detection

## Timeline
- **Week 1-2**: Implementation and testing
- **Week 3**: Staging deployment and validation
- **Week 4**: Production rollout
- **Week 5**: Monitoring and optimization

## Questions or Issues?
Contact the maintainers or open an issue on GitHub.
