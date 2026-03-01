import clsx from "clsx";
import React, { useEffect, useRef, useState } from "react";
import remarkBreaks from "remark-breaks";
import SafeMarkdown from "./SafeMarkdown";

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
  const [isFlashing, setIsFlashing] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (letterContent === "") return;
    setIsFlashing(true);
    timerRef.current = setTimeout(() => setIsFlashing(false), 1000);
    return () => {
      if (timerRef.current !== null) clearTimeout(timerRef.current);
    };
  }, [letterContent]);

  return (
    <div
      className={clsx(
        "flex-1 container relative flex flex-col md:flex-row gap-4",
        "p-4 sm:p-6",
        "bg-paper-background rounded-lg shadow-[0_4px_6px_rgba(0,0,0,0.1)]",
        "max-w-full",
        isOngoing && "h-[calc(100dvh-var(--navbar-height))]",
      )}
    >
      {letterContent !== "" ? (
        <div
          className={clsx(
            "flex flex-col gap-4 items-center flex-1/3 md:flex-2/3 h-[40%] md:h-full rounded-lg",
            isFlashing && "animate-letter-flash",
          )}
        >
          <div className="overflow-y-scroll pr-4 w-full">
            <SafeMarkdown remarkPlugins={[remarkBreaks]}>
              {letterContent}
            </SafeMarkdown>
          </div>
        </div>
      ) : null}
      <div
        className={clsx(
          "flex flex-col min-h-0 h-[60%] md:h-full",
          letterContent === "" ? "flex-1" : "flex-1/3",
        )}
      >
        {children}
      </div>
    </div>
  );
}
