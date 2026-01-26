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
      className={`
        absolute top-[50%] left-[50%] -translate-x-[50%] -translate-y-[50%]
        flex flex-col items-center justify-center gap-4
        w-[300px] sm:w-[500px] h-[300px] p-4
        rounded-lg z-10`}
    >
      {status === "idle" ? (
        <>
          <textarea
            className="h-[80%] w-full"
            placeholder="Please enter your feedback with regards to the chatbot here. A copy of your chat transcript will automatically be included with your response."
            onChange={(event) => setFeedback(event.target.value)}
          />
          <input
            className="h-[20%] w-full"
            placeholder="Enter email(s) to CC transcript separated by commas"
            type="text"
            onChange={(event) => setEmailsToCC(event.target.value)}
          />
          <input
            className="h-[20%] w-full"
            placeholder="Please enter word(s) to redact separated by commas"
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
          className={`
            text-green-dark
            border border-green-medium hover:border-green-dark
            hover:bg-green-light`}
          onClick={() => {
            if (feedback.trim() === "") handleModalClose();
            setStatus("sending");
            setTimeout(() => {
              sendFeedback(messages, feedback, emailsToCC, wordsToRedact);
              handleModalClose();
            }, 1000);
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
