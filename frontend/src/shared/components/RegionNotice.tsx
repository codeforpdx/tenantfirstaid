import { useEffect, useState } from "react";
import { useLocation } from "react-router";

const AUTO_DISMISS_MS = 8000;

/**
 * Transient banner shown after an out-of-state /chat or /letter URL is
 * redirected to Oregon, so the switch to Oregon isn't silent.
 * The trigger rides on the redirect's router location state.
 */
export default function RegionNotice() {
  const location = useLocation();
  const unsupportedRegion =
    (location.state as { unsupportedRegion?: boolean } | null)
      ?.unsupportedRegion === true;
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!unsupportedRegion) return;
    setVisible(true);
    const timer = setTimeout(() => setVisible(false), AUTO_DISMISS_MS);
    return () => clearTimeout(timer);
  }, [unsupportedRegion, location.key]);

  if (!visible) return null;

  return (
    <div
      role="status"
      className="fixed left-1/2 -translate-x-1/2 top-(--navbar-height) z-50 mt-2 flex items-center gap-3 px-4 py-2 rounded shadow-md bg-paper-background border border-gray-light text-gray-dark text-sm"
    >
      <span>
        Tenant First Aid currently only covers Oregon, so we&apos;ve switched
        you to Oregon.
      </span>
      <button
        type="button"
        onClick={() => setVisible(false)}
        aria-label="dismiss notice"
        className="font-normal shadow-none px-1 leading-none text-gray-dark hover:text-green-dark"
      >
        &times;
      </button>
    </div>
  );
}
