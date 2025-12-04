import { useState } from "react";
import sendFeedback from "../utils/feedbackHelper";
import { IMessage } from "../../../hooks/useMessages";

interface Props {
  messages: IMessage[];
  setOpenFeedback: React.Dispatch<React.SetStateAction<boolean>>;
}

export default function FeedbackModal({ messages, setOpenFeedback }: Props) {
  const [feedback, setFeedback] = useState("");
  const [wordsToRedact, setWordsToRedact] = useState("");
  const [emailsToCC, setEmailsToCC] = useState("");
  const [status, setStatus] = useState("idle");

  const handleModalClose = () => {
    setOpenFeedback(false);
    setStatus("idle");
    setFeedback("");
    setEmailsToCC("");
    setWordsToRedact("");
  };

  return (
    <dialog
      open
      className="absolute top-[50%] left-[50%] -translate-x-[50%] -translate-y-[50%] flex flex-col gap-4 items-center justify-center w-[300px] sm:w-[500px] h-[300px] rounded-lg p-4"
      aria-labelledby="feedback-title"
      aria-describedby="feedback-description"
    >
      {status === "idle" ? (
        <>
          <h2 id="feedback-title" className="sr-only">
            Feedback Form
          </h2>
          <p id="feedback-description" className="sr-only">
            Submit your feedback about the chatbot. A copy of your chat
            transcript will be included automatically.
          </p>
          <label htmlFor="feedback-text" className="sr-only">
            Your feedback
          </label>
          <textarea
            id="feedback-text"
            className="resize-none h-[80%] w-full px-3 py-2 border-1 border-[#ddd] rounded-md box-border transition-colors duration-300 focus:outline-0 focus:border-[#4a90e2] focus:shadow-[0_0_0_2px_rgba(74,144,226,0.2)]"
            placeholder="Please enter your feedback with regards to the chatbot here. A copy of your chat transcript will automatically be included with your response."
            onChange={(event) => setFeedback(event.target.value)}
            aria-required="false"
          />
          <label htmlFor="cc-emails" className="sr-only">
            Email addresses to CC
          </label>
          <input
            id="cc-emails"
            className="resize-none h-[20%] w-full px-3 py-2 border-1 border-[#ddd] rounded-md box-border transition-colors duration-300 focus:outline-0 focus:border-[#4a90e2] focus:shadow-[0_0_0_2px_rgba(74,144,226,0.2)]"
            placeholder="Enter email(s) to CC transcript separated by commas"
            type="text"
            onChange={(event) => setEmailsToCC(event.target.value)}
            aria-label="Email addresses to CC transcript"
          />
          <label htmlFor="redact-words" className="sr-only">
            Words to redact
          </label>
          <input
            id="redact-words"
            className="resize-none h-[20%] w-full px-3 py-2 border-1 border-[#ddd] rounded-md box-border transition-colors duration-300 focus:outline-0 focus:border-[#4a90e2] focus:shadow-[0_0_0_2px_rgba(74,144,226,0.2)]"
            placeholder="Please enter word(s) to redact separated by commas"
            type="text"
            onChange={(event) => setWordsToRedact(event.target.value)}
            aria-label="Words to redact from transcript"
          />
        </>
      ) : (
        <div className="flex items-center justify-center h-[80%] w-full" role="status">
          <p>Feedback Sent!</p>
        </div>
      )}
      <div className="flex gap-4">
        <button
          className="border rounded-full px-4 py-1 cursor-pointer font-semibold text-[#1F584F] transition-colors hover:bg-[#E8EEE2]"
          onClick={() => {
            if (feedback.trim() === "") handleModalClose();
            setStatus("sending");
            setTimeout(() => {
              sendFeedback(messages, feedback, emailsToCC, wordsToRedact);
              handleModalClose();
            }, 1000);
          }}
          aria-label="Send feedback"
        >
          Send
        </button>
        <button
          className="border rounded-full px-4 py-1 cursor-pointer font-semibold text-[#E3574B] transition-colors hover:bg-[#fff0ee]"
          onClick={handleModalClose}
          aria-label="Close feedback form"
        >
          Close
        </button>
      </div>
    </dialog>
  );
}
