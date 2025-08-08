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
  const [status, setStatus] = useState("idle");

  const handleModalClose = () => {
    setOpenFeedback(false);
    setStatus("idle");
    setFeedback("");
    setWordsToRedact("");
  };

  return (
    <dialog
      open
      className="absolute top-[50%] left-[50%] -translate-x-[50%] -translate-y-[50%] flex flex-col gap-4 items-center justify-center w-[300px] sm:w-[500px] h-[300px] rounded-lg p-4"
    >
      {status === "idle" ? (
        <>
          <textarea
            className="resize-none h-[80%] w-full px-3 py-2 border-1 border-[#ddd] rounded-md box-border transition-colors duration-300 focus:outline-0 focus:border-[#4a90e2] focus:shadow-[0_0_0_2px_rgba(74,144,226,0.2)]"
            placeholder="Please enter your feedback with regards to the chatbot here. A copy of your chat transcript will automatically be included with your response."
            onChange={(event) => setFeedback(event.target.value)}
          />
          <input
            className="resize-none h-[20%] w-full px-3 py-2 border-1 border-[#ddd] rounded-md box-border transition-colors duration-300 focus:outline-0 focus:border-[#4a90e2] focus:shadow-[0_0_0_2px_rgba(74,144,226,0.2)]"
            placeholder="Please enter words to redact separated by commas"
            type="text"
            onChange={(event) => setWordsToRedact(event.target.value)}
          />
        </>
      ) : (
        <div className="flex items-center justify-center h-[80%] w-full">
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
              sendFeedback(messages, feedback, wordsToRedact);
              handleModalClose();
            }, 1000);
          }}
        >
          Send
        </button>
        <button
          className="border rounded-full px-4 py-1 cursor-pointer font-semibold text-[#E3574B] transition-colors hover:bg-[#fff0ee]"
          onClick={handleModalClose}
        >
          Close
        </button>
      </div>
    </dialog>
  );
}
