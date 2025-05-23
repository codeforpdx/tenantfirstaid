import { useState } from "react";
import { IMessage } from "../../../Chat";
import useSession from "../../../hooks/useSession";

interface Props {
  message: IMessage;
  setMessages: React.Dispatch<React.SetStateAction<IMessage[]>>;
  setFeedbackSubmitted: React.Dispatch<React.SetStateAction<boolean>>;
}

export default function MessageFeedback({
  message,
  setMessages,
  setFeedbackSubmitted,
}: Props) {
  const [feedbackOpen, setFeedbackOpen] = useState<string | null>(null);
  const [betterResponse, setBetterResponse] = useState("");
  const { sessionId } = useSession();

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
          role: "assistant",
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

  return (
    <div className="feedback-section">
      {message.feedbackSubmitted === true ? (
        <div className="feedback-submitted">
          <span className="text-green-700">Thank you for your feedback!</span>
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
              onClick={() => handleFeedback(message.messageId, betterResponse)}
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
  );
}
