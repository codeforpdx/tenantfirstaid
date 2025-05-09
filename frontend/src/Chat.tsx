import { useState, useEffect, useRef } from "react";

// Generate a random session ID
const generateSessionId = (): string => {
  // Use crypto API if available for better randomness
  if (window.crypto && "randomUUID" in window.crypto) {
    return window.crypto.randomUUID();
  }

  // Fallback to a simple random string
  return (
    Math.random().toString(36).substring(2, 15) +
    Math.random().toString(36).substring(2, 15)
  );
};

interface Message {
  role: "user" | "bot";
  content: string;
  messageId: string;
  showFeedback?: boolean;
  feedbackSubmitted?: boolean;
}

export default function Chat() {
  const [text, setText] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>("");
  const [feedbackOpen, setFeedbackOpen] = useState<string | null>(null);
  const [betterResponse, setBetterResponse] = useState("");
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Initialize session ID when component mounts
  useEffect(() => {
    setSessionId(generateSessionId());
  }, []);

  const handleFeedback = async (_messageId: string, betterText: string) => {
    if (!betterText.trim()) return;

    try {
      await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          comment: betterText,
        }),
      });

      // Close feedback form and reset
      setFeedbackOpen(null);
      setBetterResponse("");
      setFeedbackSubmitted(true);

      // Add a refresh message and mark session as feedback submitted
      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          content:
            "Thank you for your feedback! Please refresh the page to start a new conversation.",
          messageId: Date.now().toString(),
          feedbackSubmitted: true,
        },
      ]);
    } catch (error) {
      console.error("Error submitting feedback:", error);
    }
  };

  const handleSend = async () => {
    // If feedback was submitted, disable further interaction
    if (feedbackSubmitted) return;

    if (!text.trim()) return;

    const userMessage = text;
    const userMessageId = Date.now().toString();
    const botMessageId = (Date.now() + 1).toString();

    setText("");
    setIsLoading(true);

    // Add user message
    setMessages((prev) => [
      ...prev,
      { role: "user", content: userMessage, messageId: userMessageId },
    ]);

    // Add empty bot message that will be updated
    setMessages((prev) => [
      ...prev,
      {
        role: "bot",
        content: "",
        messageId: botMessageId,
        showFeedback: false,
      },
    ]);

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage, session_id: sessionId }),
      });

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let fullText = "";

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value);
          fullText += chunk;

          // Update only the bot's message
          setMessages((prev) =>
            prev.map((msg) =>
              msg.messageId === botMessageId
                ? { ...msg, content: fullText }
                : msg
            )
          );
        }

        // Set showFeedback to false for all messages, then true only for the latest bot message
        setMessages((prev) =>
          prev.map((msg) =>
            msg.role === "bot"
              ? { ...msg, showFeedback: msg.messageId === botMessageId }
              : msg
          )
        );
      }
    } catch (error) {
      console.error("Error:", error);
      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.messageId === botMessageId) {
            return {
              ...msg,
              content: "Sorry, I encountered an error. Please try again.",
            };
          } else if (msg.role === "bot") {
            return { ...msg, showFeedback: false };
          }
          return msg;
        })
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    inputRef.current?.focus();
  }, [messages]);

  return (
    <div className="container">
      <h1
        style={{
          textAlign: "center",
          marginBottom: "1.5rem",
          color: "#4a90e2",
        }}
      >
        Tenant First Aid
      </h1>
      <div className="conversation">
        {messages.length > 0 ? (
          <div className="messages">
            {messages.map((message) => (
              <div
                key={message.messageId}
                className={`message ${
                  message.role === "bot" ? "bot-message" : "user-message"
                }`}
              >
                <div className="message-content">
                  <strong>{message.role === "bot" ? "Bot: " : "You: "}</strong>
                  {message.role === "bot" &&
                  message.content === "" &&
                  isLoading ? (
                    <span className="dot-pulse">...</span>
                  ) : (
                    <span style={{ whiteSpace: "pre-wrap" }}>
                      {message.content}
                    </span>
                  )}
                </div>

                {message.role === "bot" && message.showFeedback && (
                  <div className="feedback-section">
                    {message.feedbackSubmitted === true ? (
                      <div className="feedback-submitted">
                        <span style={{ color: "green" }}>
                          Thank you for your feedback!
                        </span>
                      </div>
                    ) : feedbackOpen === message.messageId ? (
                      <div className="feedback-form">
                        <textarea
                          placeholder="Describe the preferred behavior"
                          value={betterResponse}
                          onChange={(e) => setBetterResponse(e.target.value)}
                          rows={4}
                          style={{ width: "100%", marginBottom: "8px" }}
                        />
                        <div>
                          <button
                            onClick={() =>
                              handleFeedback(message.messageId, betterResponse)
                            }
                            disabled={!betterResponse.trim()}
                            style={{ marginRight: "8px" }}
                          >
                            Submit
                          </button>
                          <button onClick={() => setFeedbackOpen(null)}>
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <button
                        onClick={() => setFeedbackOpen(message.messageId)}
                        className="thumbs-down"
                        title="Provide better response"
                        style={{
                          background: "none",
                          border: "none",
                          cursor: "pointer",
                          fontSize: "16px",
                          padding: "4px",
                          color: "#888",
                        }}
                      >
                        👎 This response could be better
                      </button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p style={{ textAlign: "center", color: "#888" }}>
            Ask me anything about tenant rights and assistance.
          </p>
        )}
      </div>
      <div
        style={{
          display: "flex",
          gap: "0.5rem",
          marginTop: "1rem",
          alignItems: "stretch",
        }}
      >
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault(); // prevent form submission or newline
              handleSend();
            }
          }}
          className="input"
          style={{ margin: 0 }}
          placeholder={
            feedbackSubmitted
              ? "Please refresh the page to start a new conversation"
              : "Type your message here..."
          }
          disabled={isLoading || feedbackSubmitted}
          ref={inputRef}
        />
        <button
          className="button"
          onClick={handleSend}
          disabled={isLoading || !text.trim() || feedbackSubmitted}
        >
          {isLoading ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}
