import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

export default function PromptEditor() {
  const [prompt, setPrompt] = useState<string>("");
  const [editValue, setEditValue] = useState<string>("");
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [error, setError] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const navigate = useNavigate();

  /** Fetch current prompt immediately after mount */
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/prompt");
        if (!res.ok) throw new Error();
        const data = (await res.json()) as { prompt: string };
        setPrompt(data.prompt);
        setEditValue(data.prompt);
      } catch {
        setPrompt("server error");
        setEditValue("server error");
        setError(true);
      } finally {
        setLoading(false);
      }
    })();
  }, []);
  const handleUnauthorized = () => {
    localStorage.removeItem("password");
    navigate("/", { replace: true });
  };

  /** Handlers */
  const startEditing = () => !loading && setIsEditing(true);
  const cancelEditing = () => {
    setIsEditing(false);
    setEditValue(prompt);
  };
  const applyEdit = async () => {
    try {
      const res = await fetch("/api/prompt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: editValue,
          password: localStorage.getItem("password"),
        }),
      });
      if (res.status === 401) {
        handleUnauthorized();
        return;
      }
      if (!res.ok) throw new Error();
      const data = (await res.json()) as { prompt: string };
      setPrompt(data.prompt);
      setEditValue(data.prompt);
      setIsEditing(false);
      setError(false);
    } catch {
      setError(true);
    }
  };

  const restoreDefault = async () => {
    try {
      const res = await fetch("/api/prompt?default=true", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: localStorage.getItem("password") }),
      });
      if (res.status === 401) return handleUnauthorized();
      if (!res.ok) throw new Error();
      const data = (await res.json()) as { prompt: string };
      setPrompt(data.prompt);
      setEditValue(data.prompt);
      setIsEditing(false);
      setError(false);
    } catch {
      setError(true);
    }
  };

  return (
    <div className="container my-10 mx-auto p-6 bg-white rounded-lg max-w-[600px] shadow-[0_4px_6px_rgba(0,0,0,0.1)]">
      {/* header row */}
      <div className="flex justify-between items-center">
        <h2 className="m-0">Prompt Editing</h2>
        <Link
          to="/"
          className="py-1.5 px-4 bg-[#4a90e2] hover:bg-[#3a7bc8] text-white rounded-md cursor-pointer transition-color duration-300"
        >
          Chat
        </Link>
      </div>

      {/* prompt display / editor */}
      <label className="font-semibold block my-4 ml-0 mr-1">
        Current prompt
      </label>

      {isEditing ? (
        <textarea
          className="w-full p-3 border-1 border-[#ddd] rounded-md box-border transition-colors duration-300 focus:outline-0 focus:border-[#4a90e2] focus:shadow-[0_0_0_2px_rgba(74,144,226,0.2)]"
          rows={4}
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
        />
      ) : (
        <div className="mb-4 overflow-y-auto max-h-[400px] p-2 rounded-md bg-[#fafafa] flex min-h-16 items-center">
          {loading ? (
            <span className="dot-pulse italic">Loading…</span>
          ) : (
            <p className="p-2 mt-8 mb-0 rounded-sm">{prompt}</p>
          )}
        </div>
      )}

      {error && (
        <p className="text-red-500 mt-1">Server error. Please try again.</p>
      )}

      {/* action buttons */}
      {isEditing ? (
        <div className="flex gap-1 justify-end">
          <button
            className="py-1.5 px-4 bg-[#ddd] text-[#333] rounded-md cursor-pointer transition-color duration-300"
            onClick={cancelEditing}
          >
            Cancel
          </button>
          <button
            className="py-1.5 px-4 bg-[#4a90e2] hover:bg-[#3a7bc8] text-white rounded-md cursor-pointer transition-color duration-300"
            onClick={applyEdit}
          >
            Apply
          </button>
        </div>
      ) : (
        <div className="flex gap-1 justify-end">
          <button
            className="py-1.5 px-4 bg-[#ddd] text-[#333] rounded-md cursor-pointer transition-color duration-300"
            onClick={restoreDefault}
            disabled={loading}
          >
            Restore default
          </button>
          <button
            className="py-1.5 px-4 bg-[#4a90e2] hover:bg-[#3a7bc8] text-white rounded-md cursor-pointer transition-color duration-300"
            onClick={startEditing}
            disabled={loading}
          >
            Edit
          </button>
        </div>
      )}
    </div>
  );
}
