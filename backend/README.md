# Tenant First Aid Backend

Flask backend API for the Tenant First Aid chatbot.

## Development Setup

See the main [README.md](../README.md) for full setup instructions.

## API Endpoints

- `/api/init` - Initialize chat session
- `/api/query` - Send chat message
- `/api/history` - Get chat history
- `/api/clear-session` - Clear current session
- `/api/citation` - Get citation information
- `/api/version` - Get application version

## Version Management

This backend uses `setuptools-scm` for automatic version management based on Git tags. The version is dynamically generated from the repository's tag history.

### Checking Version

```bash
# In the backend directory
uv run python -c "from importlib.metadata import version; print(version('tenant-first-aid'))"

# Or via the API
curl http://localhost:5001/api/version
```

### Creating a New Release

1. Ensure all changes are committed and pushed
2. Create a new tag following semantic versioning:
   ```bash
   git tag v0.3.0  # or appropriate version
   git push origin v0.3.0
   ```
3. The version will automatically be updated in the application

## Development Commands

From the `backend/` directory:

```bash
# Install dependencies
uv sync

# Run the server
uv run python -m tenantfirstaid.app

# Run tests
uv run pytest

# Format code
uv run ruff format

# Lint code
uv run ruff check

# Type check
uv run ty check
```