import clsx from "clsx";
import FrequentInquiries from "../shared/components/FrequentInquiries";
import MessageContainer from "../shared/components/MessageContainer";
import FeaturesPanel from "../shared/components/FeaturesPanel";
import MobilePanel from "../shared/components/MobilePanel";

interface Props {
  isOngoing: boolean;
  letterContent: string;
  disclaimer: React.ReactNode;
  children: React.ReactNode;
}

/**
 * Shared layout for the chat and letter pages: the message pane, the
 * Frequent Inquiries side panel, and the features panel.
 */
export default function ChatPageLayout({
  isOngoing,
  letterContent,
  disclaimer,
  children,
}: Props) {
  return (
    <div className="min-h-full lg:h-full w-full flex flex-col lg:flex-row transition-all duration-300 lg:relative lg:bg-paper-background">
      <div className="flex-1 lg:my-0 w-full lg:flex-1 flex lg:order-2">
        <MessageContainer isOngoing={isOngoing} letterContent={letterContent}>
          {children}
        </MessageContainer>
      </div>
      <div
        className={clsx(
          "flex flex-col w-full bg-paper-background",
          "border-b lg:border-b-0 border-gray-light",
          "lg:order-1 lg:my-0 lg:w-1/5 lg:border-r",
          "[@media(max-height:800px)]:my-0 [@media(max-height:800px)]:self-stretch [@media(max-height:800px)]:overflow-hidden",
        )}
      >
        <MobilePanel title="Frequent Inquiries">
          <div className="flex-1 min-h-0 lg:overflow-y-auto [@media(max-height:800px)]:overflow-y-auto">
            <FrequentInquiries />
          </div>
        </MobilePanel>
      </div>
      <FeaturesPanel disclaimer={disclaimer} />
    </div>
  );
}
