import React from "react";

interface Props {
  isOngoing: boolean;
  letterContent: string;
  children: React.ReactNode;
}

export default function MessageContainer({
  isOngoing,
  letterContent,
  children,
}: Props) {
  return (
    <div
      className={`
        flex-1 container relative
        flex flex-col md:flex-row gap-4
        p-4 sm:p-6 bg-paper-background rounded-lg
        shadow-[0_4px_6px_rgba(0,0,0,0.1)]
        max-w-full
        ${
          isOngoing
            ? `h-[calc(100dvh-var(--mobile-offset-message-container)-var(--navbar-height))]
            md:h-[calc(100dvh-var(--desktop-offset-message-container)-var(--navbar-height))]`
            : ""
        }`}
    >
      {letterContent !== "" ? (
        <div className="flex flex-col gap-4 items-center flex-1/3 md:flex-2/3 h-[40%] md:h-full">
          <div className="overflow-y-scroll pr-4 w-full">
            <span
              className="whitespace-pre-wrap generated-letter"
              dangerouslySetInnerHTML={{
                __html: letterContent,
              }}
            />
          </div>
        </div>
      ) : null}
      <div
        className={`flex flex-col ${letterContent === "" ? "flex-1" : "flex-1/3"} h-[60%] md:h-full`}
      >
        {children}
      </div>
    </div>
  );
}
