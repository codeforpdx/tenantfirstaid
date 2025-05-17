import { useState, useEffect, useRef } from "react";
import ExportMessagesButton from "./pages/Chat/components/ExportMessagesButton";
import { useNavigate } from "react-router-dom";


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

export interface IMessage {
  role: "user" | "bot";
  content: string;
  messageId: string;
  showFeedback?: boolean;
  feedbackSubmitted?: boolean;
}

export default function Chat() {
  const [text, setText] = useState("");
  const [messages, setMessages] = useState<IMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>("");
  const [feedbackOpen, setFeedbackOpen] = useState<string | null>(null);
  const [betterResponse, setBetterResponse] = useState("");
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const navigate = useNavigate();
  // Initialize session ID when component mounts
  useEffect(() => {
    // Get chat history
    const fetchChatHistory = async (sessionId: string) => {
      setIsLoading(true);
      try {
        const res = await fetch(`/api/history/${sessionId}`, {
          method: "GET",
          headers: { "Content-Type": "application/json" }
        })

        if (!res.ok) {
          console.error('Failed to fetch chat history.', res.status, res.statusText);
        }

        // `messageId` is not currently used by the backend,
        // so let's generate some dummy IDs to play nice with React.
        // We increment each time to avoid duplicate keys.
        let history: IMessage[] = await res.json();
        let messageId = Date.now();
        history = history.map((message: IMessage) => {
          messageId++;
          message.messageId = messageId.toString();
          return message;
        });
        setMessages(history);
      } catch (err) {
        console.error("Error fetching chat history", err);
      } finally {
        setIsLoading(false);
      }
    }

    const cachedSessionId = localStorage.getItem("sessionId");
    if (cachedSessionId === null) {
      const newSessionId = generateSessionId();
      localStorage.setItem("sessionId", newSessionId);
      setSessionId(newSessionId);
    } else {
      setSessionId(cachedSessionId);
      fetchChatHistory(cachedSessionId);
    }
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

  const handleClearSession = async () => {
    const newSessionId = generateSessionId();
    localStorage.setItem("sessionId", newSessionId);
    setSessionId(newSessionId);
    setMessages([]);
  }

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
    <div className="container relative mx-auto flex flex-col">
      <div className="relative">
        <h1 className="text-3xl text-center mb-6 mt-5 text-[#4a90e2] hover:bd-[#3a7bc8]">
          <strong>Tenant First Aid</strong>
        </h1>
        <ExportMessagesButton messages={messages} />
      </div>
      <div className="conversation">
        {messages.length > 0 ? (
          <div className="messages">
            {messages.map((message) => (
              <div
                key={message.messageId}
                className={`message ${message.role === "bot" ? "bot-message" : "user-message"
                  }`}
              >
                <div className="message-content">
                  <strong>{message.role === "bot" ? "Bot: " : "You: "}</strong>
                  {message.role === "bot" &&
                    message.content === "" &&
                    isLoading ? (
                    <span className="dot-pulse">...</span>
                  ) : (
                    <span className="whitespace-pre-wrap">
                      {message.content}
                    </span>
                  )}
                </div>

                {message.role === "bot" && message.showFeedback && (
                  <div className="feedback-section">
                    {message.feedbackSubmitted === true ? (
                      <div className="feedback-submitted">
                        <span className="text-green-700">
                          Thank you for your feedback!
                        </span>
                      </div>
                    ) : feedbackOpen === message.messageId ? (
                      <div className="feedback-form">
                        <textarea
                          className="w-full p-3 border-1 border-[#ddd] rounded-md box-border transition-colors duration-300 focus:outline-0 focus:border-[#4a90e2] focus:shadow-[0_0_0_2px_rgba(74,144,226,0.2)]"
                          placeholder="Describe the preferred behavior"
                          value={betterResponse}
                          onChange={(e) => setBetterResponse(e.target.value)}
                          rows={4}
                        />
                        <div className="flex gap-2">
                          <button
                            className="py-1.5 px-4 bg-[#4a90e2] hover:bg-[#3a7bc8] text-white rounded-md cursor-pointer transition-color duration-300"
                            onClick={() =>
                              handleFeedback(message.messageId, betterResponse)
                            }
                            disabled={!betterResponse.trim()}
                          >
                            Submit
                          </button>
                          <button
                            className="py-1.5 px-4 bg-[#ddd] text-[#333] rounded-md cursor-pointer transition-color duration-300"
                            onClick={() => setFeedbackOpen(null)}
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <button
                        onClick={() => setFeedbackOpen(message.messageId)}
                        className="bg-none border-none cursor-pointer p-1 text-[#888]"
                        title="Provide better response"
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
          <p className="text-center text-[#888]">
            Ask me anything about tenant rights and assistance.
          </p>
        )}
      </div>
      <div className="flex gap-2 mt-4 h-11 items-stretch">
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
          className="w-full p-3 border-1 border-[#ddd] rounded-md box-border transition-colors duration-300 focus:outline-0 focus:border-[#4a90e2] focus:shadow-[0_0_0_2px_rgba(74,144,226,0.2)]"
          placeholder={
            feedbackSubmitted
              ? "Please refresh the page to start a new conversation"
              : "Type your message here..."
          }
          disabled={isLoading || feedbackSubmitted}
          ref={inputRef}
        />
        <button
          className="px-6 bg-[#4a90e2] hover:bg-[#3a7bc8] text-white rounded-md cursor-pointer transition-color duration-300"
          onClick={handleSend}
          disabled={isLoading || !text.trim() || feedbackSubmitted}
        >
          {isLoading ? "..." : "Send"}
        </button>
      </div>
      <button
        className="fixed bottom-6 right-1/4 translate-x-1/2 sm:right-8 sm:translate-x-0 bg-white border border-[#4a90e2] text-[#4a90e2] hover:bg-[#4a90e2] hover:text-white rounded-full shadow-lg px-6 py-3 font-semibold transition-colors duration-300 cursor-pointer z-50"
        onClick={() => navigate("/about")}
        title="About Us"

      >
        About Tenant First Aid
      </button>
    </div>
  );
}
