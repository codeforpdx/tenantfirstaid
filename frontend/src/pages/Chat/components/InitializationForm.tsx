import type { ChatMessage } from "../../../shared/types/messages";
import BeaverIcon from "../../../shared/components/BeaverIcon";
import type { AddMessage } from "../../../hooks/useMessages";
import { streamText } from "../utils/streamHelper";
import { createId } from "../../../shared/utils/createId";
import useHousingContext from "../../../hooks/useHousingContext";
import { buildLocationPrefix } from "../../../shared/utils/buildLocationPrefix";
import { scrollToTop } from "../../../shared/utils/scrolling";
import { HumanMessage } from "@langchain/core/messages";

interface Props {
  addMessage: AddMessage;
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  setIsLoading: React.Dispatch<React.SetStateAction<boolean>>;
}

/**
 * Initial chat form for describing a housing issue.
 * The jurisdiction is set via the navbar location picker.
 */
export default function InitializationForm({
  addMessage,
  setMessages,
  setIsLoading,
}: Props) {
  const {
    housingLocation,
    issueDescription,
    handleIssueDescription,
    handleFormReset,
  } = useHousingContext();

  const handleInitialInput = async () => {
    const content = [
      buildLocationPrefix(housingLocation.city, housingLocation.state),
      issueDescription,
    ]
      .join(" ")
      .trim();
    const userMessage = new HumanMessage({
      content,
      id: createId(),
    });
    setMessages((prev) => [...prev, userMessage]);

    await streamText({
      addMessage,
      history: [userMessage],
      setMessages,
      housingLocation,
      setIsLoading,
    });
  };

  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        handleInitialInput();
      }}
    >
      <div className="flex px-4 gap-2 items-center justify-center">
        <div>
          <BeaverIcon />
        </div>
        <div className="">
          <p className="text-lg sm:text-xl text-center">
            Welcome to Tenant First Aid!
          </p>
        </div>
      </div>
      <div>
        <div className="border rounded-lg px-4 py-2">
          <p>Things to keep in mind!</p>
          <ul className="list-disc pl-4">
            <li>Tenants have rights under state and local law.</li>
            <li>
              The type of housing you live in may determine what legal
              protections apply to you.
            </li>
            <li>
              In most cases, landlords must go through a specific legal process
              in order to get you to move out (eviction).
            </li>
          </ul>
        </div>
      </div>
      <div>
        <textarea
          className="h-25 md:h-16 w-full"
          placeholder="Briefly describe your specific housing situation or question about housing."
          value={issueDescription}
          onChange={handleIssueDescription}
        />
      </div>

      <div className="flex justify-center gap-4">
        <button
          className="text-red-dark border border-red-medium hover:border-red-dark hover:bg-red-light"
          type="reset"
          onClick={handleFormReset}
        >
          Reset
        </button>
        <button
          className="text-green-dark border border-green-medium hover:border-green-dark hover:bg-green-light"
          type="submit"
          aria-label="enter chat"
          title="Enter Chat"
          onClick={() => scrollToTop()}
        >
          Start Chat
        </button>
      </div>
    </form>
  );
}
