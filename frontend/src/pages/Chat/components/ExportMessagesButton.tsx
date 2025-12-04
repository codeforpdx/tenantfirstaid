import { IMessage } from "../../../hooks/useMessages";
import exportMessages from "../utils/exportHelper";

interface Props {
  messages: IMessage[];
}

export default function ExportMessagesButton({ messages }: Props) {
  return (
    <button
      className="border text-sm sm:text-base shadow-sm border-[#4a90e2] text-[#4a90e2] hover:bg-[#E6F0FB] transition-colors"
      onClick={() => exportMessages(messages)}
    >
      Export
    </button>
  );
}
