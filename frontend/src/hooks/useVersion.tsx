import { useState, useEffect } from "react";

interface VersionResponse {
  version: string;
  error?: string;
}

export function useVersion() {
  const [version, setVersion] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchVersion = async () => {
      try {
        const response = await fetch("/api/version");
        const data: VersionResponse = await response.json();

        if (response.ok) {
          setVersion(data.version);
        } else {
          setError("Failed to fetch version");
        }
      } catch (err) {
        setError("Failed to fetch version");
      } finally {
        setLoading(false);
      }
    };

    fetchVersion();
  }, []);

  return { version, loading, error };
}
