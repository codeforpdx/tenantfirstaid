import { useState } from "react";
import clsx from "clsx";
import ChevronRight from "./ChevronRight";
import MobilePanel from "./MobilePanel";
import FeatureSnippet from "./FeatureSnippet";
import { useIsMobile } from "../../hooks/useIsMobile";
import { readStorage, writeStorage } from "../utils/storage";

type CSSVars = React.CSSProperties & { "--features-w"?: string };

interface Props {
  disclaimer: React.ReactNode;
}

export default function FeaturesPanel({ disclaimer }: Props) {
  const isMobile = useIsMobile();
  const [open, setOpen] = useState(() => {
    const saved = readStorage("featuresPanelOpen");
    return saved === null ? true : saved === "true";
  });

  return (
    <>
      <button
        type="button"
        aria-expanded={open}
        aria-controls="features-panel-content"
        aria-label="Toggle Features panel"
        onClick={() => {
          setOpen(!open);
          writeStorage("featuresPanelOpen", String(!open));
        }}
        className={clsx(
          "hidden lg:flex items-center justify-center",
          "absolute top-4 z-10",
          "w-6 h-6 bg-paper-background border border-gray-light rounded-l-md",
          "transition-[right] duration-300 ease-in-out",
          open ? "right-[20%]" : "right-0",
        )}
      >
        <span
          className={clsx(
            "transition-transform duration-300",
            open ? "rotate-0" : "rotate-180",
          )}
        >
          <ChevronRight size={14} />
        </span>
      </button>
        <div
          style={{ "--features-w": "20vw" } as CSSVars}
        className={clsx(
          "flex flex-col w-full bg-paper-background",
          "border-b lg:border-b-0 border-gray-light",
          "lg:order-3 lg:my-0 lg:ml-auto",
          "lg:transition-[width] lg:duration-300 lg:ease-in-out overflow-hidden",
          open ? "lg:w-[var(--features-w)]" : "lg:w-0",
          "[@media(max-height:800px)]:my-0 [@media(max-height:800px)]:self-stretch [@media(max-height:800px)]:overflow-hidden",
        )}
      >
        <div
          id="features-panel-content"
          inert={(!isMobile && !open) || undefined}
          className={clsx(
            "flex-1 flex flex-col min-w-0 min-h-0 lg:border-l border-gray-light",
            "lg:transition-opacity lg:duration-300",
            "lg:w-[var(--features-w)]",
            open ? "lg:opacity-100" : "lg:opacity-0 lg:pointer-events-none",
          )}
        >
          <MobilePanel title="Features">
            <div className="flex flex-col flex-1 min-h-0 lg:overflow-y-auto [@media(max-height:800px)]:overflow-y-auto">
              <FeatureSnippet />
            </div>
          </MobilePanel>
          <div className="p-4 border-t border-gray-light lg:border-t-0 [@media(min-width:1024px)_and_(min-height:801px)]:mt-auto">
            {disclaimer}
          </div>
        </div>
      </div>
    </>
  );
}
