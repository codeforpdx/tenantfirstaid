import { useEffect, useState } from "react";
import sendFeedback from "../utils/feedbackHelper";
import type { ChatMessage } from "../../../shared/types/messages";

const AUTO_CLOSE_DELAY_MS = 1500;

interface Props {
  messages: ChatMessage[];
  setOpenFeedback: React.Dispatch<React.SetStateAction<boolean>>;
}

/**
 * Dialog for submitting feedback with optional email CC and word redaction.
 */
export default function FeedbackModal({ messages, setOpenFeedback }: Props) {
  const [feedback, setFeedback] = useState("");
  const [wordsToRedact, setWordsToRedact] = useState("");
  const [emailsToCC, setEmailsToCC] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">(
    "idle",
  );
  const canEdit = status === "idle" || status === "error";

  const handleModalClose = () => {
    setOpenFeedback(false);
    setStatus("idle");
    setFeedback("");
    setEmailsToCC("");
    setWordsToRedact("");
  };

  // Unmounting the modal resets its state, so closing is enough; the cleanup
  // cancels the timer if the user clicks Close first.
  useEffect(() => {
    if (status !== "sent") return;
    const timer = setTimeout(() => setOpenFeedback(false), AUTO_CLOSE_DELAY_MS);
    return () => clearTimeout(timer);
  }, [status, setOpenFeedback]);

  return (
    <dialog
      open
      className={`
        absolute top-[50%] left-[50%] -translate-x-[50%] -translate-y-[50%]
        flex flex-col items-center justify-center gap-4
        w-[300px] sm:w-[500px] h-[300px] p-4
        rounded-lg z-10`}
    >
      {canEdit ? (
        <>
          {status === "error" && (
            <p role="alert" className="text-red-dark">
              Couldn't send feedback. Please try again.
            </p>
          )}
          <textarea
            className="h-[80%] w-full"
            placeholder="Please enter your feedback with regards to the chatbot here. A copy of your chat transcript will automatically be included with your response."
            value={feedback}
            onChange={(event) => setFeedback(event.target.value)}
          />
          <input
            className="h-[20%] w-full"
            placeholder="Enter email(s) to CC transcript separated by commas"
            type="text"
            value={emailsToCC}
            onChange={(event) => setEmailsToCC(event.target.value)}
          />
          <input
            className="h-[20%] w-full"
            placeholder="Please enter word(s) to redact separated by commas"
            type="text"
            value={wordsToRedact}
            onChange={(event) => setWordsToRedact(event.target.value)}
          />
        </>
      ) : (
        <div className="flex items-center justify-center h-[80%] w-full">
          <p>{status === "sending" ? "Sending…" : "Feedback Sent!"}</p>
        </div>
      )}
      <div className="flex gap-4">
        <button
          className={`
            text-green-dark
            border border-green-medium hover:border-green-dark
            hover:bg-green-light`}
          disabled={!canEdit}
          onClick={async () => {
            if (feedback.trim() === "") {
              handleModalClose();
              return;
            }
            setStatus("sending");
            try {
              await sendFeedback(messages, feedback, emailsToCC, wordsToRedact);
              setStatus("sent");
            } catch (error) {
              console.error("Failed to send feedback:", error);
              setStatus("error");
            }
          }}
        >
          Send
        </button>
        <button
          className={`
            text-red-dark
            border border-red-medium hover:border-red-dark
            hover:bg-red-light`}
          onClick={handleModalClose}
        >
          Close
        </button>
      </div>
    </dialog>
  );
}
