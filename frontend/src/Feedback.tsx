import React, { useState, useEffect } from "react";

type MessageType = {
  role: string;
  content: string;
};

type ConversationType = {
  conversation: MessageType[];
  feedback: string;
};

type FeedbackEntryType = {
  prompt: string;
  conversations: ConversationType[];
};

type Props = {
  feedbackData: FeedbackEntryType[];
};

function FeedbackContent({ feedbackData }: Props) {
  const [selectedPromptIndex, setSelectedPromptIndex] = useState<number | null>(
    null
  );

  return (
    <div style={{ display: "flex", gap: "2rem" }}>
      {/* Prompt list */}
      <div style={{ width: "300px", overflowY: "auto" }}>
        <h3>Prompts</h3>
        <ul style={{ listStyle: "none", padding: 0 }}>
          {feedbackData.map((entry, index) => (
            <li
              key={index}
              style={{
                cursor: "pointer",
                padding: "0.5rem",
                background:
                  selectedPromptIndex === index ? "#eee" : "transparent",
                whiteSpace: "normal",
                overflowWrap: "anywhere",
                wordBreak: "break-word",
                display: "block", // not inline or flex
              }}
              onClick={() => setSelectedPromptIndex(index)}
            >
              {entry.prompt}
            </li>
          ))}
        </ul>
      </div>

      {/* Conversations */}
      <div style={{ flex: 1 }}>
        <h3>Conversations</h3>
        {selectedPromptIndex === null ? (
          <p>Select a prompt to view conversations.</p>
        ) : (
          feedbackData[selectedPromptIndex].conversations.map((conv, i) => (
            <div
              key={i}
              style={{
                marginBottom: "1rem",
                borderBottom: "1px solid #ccc",
                paddingBottom: "0.5rem",
              }}
            >
              <div>
                <strong>Conversation:</strong>{" "}
                {conv.conversation
                  .map((msg) => `${msg.role}: ${msg.content}`)
                  .join(" | ")}
              </div>
              <div>
                <strong>Feedback:</strong> {conv.feedback}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default function FeedbackGate() {
  const [password, setPassword] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState("");
  const [feedback, setFeedback] = useState<FeedbackEntryType[] | null>(null);
  const [loading, setLoading] = useState(false);

  // Get password from localStorage on mount
  useEffect(() => {
    const storedPassword = localStorage.getItem("password");
    if (storedPassword) {
      setPassword(storedPassword);
    }
  }, []);

  // Fetch feedback if password is set and feedback not yet loaded
  useEffect(() => {
    const fetchFeedback = async () => {
      setLoading(true);
      try {
        const res = await fetch("/api/get_feedback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ password }),
        });

        if (!res.ok) {
          alert(`Failed to fetch feedback: ${res.status} ${res.statusText}`);
          localStorage.removeItem("password");
          setPassword(null);
          return;
        }

        const data: { feedback: FeedbackEntryType[] } = await res.json();
        setFeedback(data.feedback);
      } catch (err) {
        console.error("Error fetching feedback:", err);
        alert("Network error while fetching feedback.");
        localStorage.removeItem("password");
        setPassword(null);
      } finally {
        setLoading(false);
      }
    };

    if (password && !feedback && !loading) {
      fetchFeedback();
    }
  }, [password, feedback, loading]);

  const handleSubmit = () => {
    if (inputValue) {
      localStorage.setItem("password", inputValue);
      setPassword(inputValue);
    }
  };

  if (!password) {
    return (
      <div className="container">
        <label>
          Password:
          <input
            type="password"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
          />
        </label>
        <button className="button" onClick={handleSubmit}>
          Submit
        </button>
      </div>
    );
  }

  if (loading) {
    return <p>Loading...</p>;
  }

  if (feedback) {
    return <FeedbackContent feedbackData={feedback} />;
  }

  return null;
}
