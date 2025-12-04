import { useLocation } from "react-router-dom";

interface Props {
  ref: React.RefObject<HTMLDialogElement | null>;
}

export default function LetterGenerationDialog({ ref }: Props) {
  const location = useLocation();
  const isRedirected = location.pathname !== "/letter";
  const redirectMessage = isRedirected
    ? "You've been redirected here so we can help you create a letter to your landlord. "
    : "";
  const followUpMessage = isRedirected
    ? " Once your letter is complete, you should go back to your previous page and follow the remaining steps."
    : "";

  return (
    <dialog
      ref={ref}
      aria-label="letter-dialog-modal"
      aria-labelledby="letter-dialog-title"
      aria-describedby="letter-dialog-description"
      className="rounded-lg p-6 min-w-[300px] max-w-[600px] fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
    >
      <div className="flex flex-col items-end">
        <h2 id="letter-dialog-title" className="sr-only">
          Letter Generation Notice
        </h2>
        <p id="letter-dialog-description">
          {redirectMessage}
          It'll take a few seconds to complete your initial letter. You could
          instruct the tool to update the letter to your liking after it's
          generated.
          {followUpMessage}
        </p>
        <button
          onClick={() => ref.current?.close()}
          className="underline text-blue-600 hover:text-blue-500 text-sm"
          aria-label="close-dialog"
        >
          Close
        </button>
      </div>
    </dialog>
  );
}
