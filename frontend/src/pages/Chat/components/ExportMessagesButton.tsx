import { IMessage } from "../../../hooks/useMessages";
import exportMessages from "../utils/exportHelper";

interface Props {
  messages: IMessage[];
}

export default function ExportMessagesButton({ messages }: Props) {
  return (
    <button
      className={`
        text-sm sm:text-base text-blue-dark
        border border-blue-medium hover:border-blue-dark
        hover:bg-blue-light`}
      onClick={() => exportMessages(messages)}
    >
      Export
    </button>
  );
}
