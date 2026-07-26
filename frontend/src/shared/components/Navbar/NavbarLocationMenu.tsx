import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import useActiveJurisdiction from "../../../hooks/useActiveJurisdiction";

/**
 * Desktop navbar dropdown for picking the active jurisdiction. Selecting an
 * option updates the shared location that the Chat and Letter links carry.
 */
export default function NavbarLocationMenu() {
  const { active, options, selectLocation } = useActiveJurisdiction();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Brief delay before closing so moving the mouse from the trigger to the
  // menu (or back) doesn't snap it shut.
  const CLOSE_DELAY_MS = 200;

  const cancelClose = () => {
    if (closeTimer.current !== null) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  };

  const openNow = () => {
    cancelClose();
    setOpen(true);
  };

  const scheduleClose = () => {
    cancelClose();
    closeTimer.current = setTimeout(() => setOpen(false), CLOSE_DELAY_MS);
  };

  useEffect(() => {
    if (!open) return undefined;
    const handlePointerDown = (event: MouseEvent) => {
      if (
        event.target instanceof Node &&
        !containerRef.current?.contains(event.target)
      )
        setOpen(false);
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  useEffect(() => cancelClose, []);

  return (
    <div
      ref={containerRef}
      className="relative"
      onMouseEnter={openNow}
      onMouseLeave={scheduleClose}
    >
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={openNow}
        onFocus={openNow}
        className={clsx(
          // Override the global <button> base styles so the trigger matches the
          // plain navbar links (no drop shadow, normal weight).
          "px-2 py-0 font-normal shadow-none text-paper-background",
          "hover:text-green-dark hover:bg-green-light hover:opacity-70 hover:rounded",
        )}
      >
        Location: {active.label}
      </button>
      {open && (
        // Transparent top padding both clears the navbar's bottom padding (so
        // the menu drops below the bar, not over it) and bridges the gap so the
        // cursor never crosses a dead zone on its way to the menu items.
        <div className="absolute left-0 top-full pt-4 z-50">
          <ul
            role="menu"
            className="min-w-44 rounded bg-paper-background shadow-lg py-1"
          >
            {options.map((option) => (
              <li role="none" key={option.key}>
                <button
                  type="button"
                  role="menuitemradio"
                  aria-checked={active.key === option.key}
                  onClick={() => {
                    selectLocation(option);
                    setOpen(false);
                  }}
                  className={clsx(
                    "block w-full text-left px-4 py-2 font-normal shadow-none rounded-none text-gray-dark",
                    "hover:bg-green-medium hover:text-paper-background",
                    active.key === option.key && "bg-green-background",
                  )}
                >
                  {option.label}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
