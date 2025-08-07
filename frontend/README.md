# Tenant First Aid Frontend

React frontend application for the Tenant First Aid chatbot.

## Development Setup

See the main [README.md](../README.md) for full setup instructions.

## Version Display

The application version is automatically fetched from the backend API and displayed in the navigation sidebar. The version corresponds to the backend version derived from Git tags.

### Version Hook

The frontend includes a custom `useVersion` hook that fetches version information from `/api/version`:

```typescript
import { useVersion } from "./hooks/useVersion";

function MyComponent() {
  const { version, loading, error } = useVersion();
  
  return (
    <div>
      {loading ? "Loading..." : error ? "Version unavailable" : `v${version}`}
    </div>
  );
}
```

## Development Commands

From the `frontend/` directory:

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Lint code
npm run lint

# Format code
npm run format

# Preview production build
npm run preview
```

## Creating a New Release

The frontend version automatically reflects the backend version. To create a new release:

1. Ensure all changes are committed and pushed to the main branch
2. Create and push a new Git tag:
   ```bash
   git tag v0.3.0  # Follow semantic versioning
   git push origin v0.3.0
   ```
3. The version will automatically be updated and displayed in the UI

## Architecture

- **React 19** with TypeScript
- **Vite** for build tooling and development server
- **Tailwind CSS** for styling
- **React Router** for navigation
- **TanStack Query** for API state management