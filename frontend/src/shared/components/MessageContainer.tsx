import { ReactNode } from "react";

interface Props {
  isOngoing: boolean;
  letterContent: string;
  children: ReactNode;
}

export default function MessageContainer({
  isOngoing,
  letterContent,
  children,
}: Props) {
  const MOBILE_OFFSET_HEIGHT = 4;
  const DESKTOP_OFFSET_HEIGHT = 10;

  return (
    <div
      className={`container relative flex flex-col md:flex-row mx-auto gap-4 p-4 sm:p-6 bg-[#F4F4F2] rounded-lg shadow-[0_4px_6px_rgba(0,0,0,0.1)]
        ${
          isOngoing
            ? `justify-between h-[calc(100dvh-${MOBILE_OFFSET_HEIGHT}rem-var(--navbar-height))] md:h-[calc(100dvh-${DESKTOP_OFFSET_HEIGHT}rem-var(--navbar-height))]`
            : "justify-center max-w-[600px]"
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
