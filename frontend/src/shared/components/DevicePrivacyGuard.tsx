import { useEffect, useRef, useState } from "react";
import {
  readSessionStorage,
  removeSessionStorage,
  removeSessionStorageByPrefix,
  writeSessionStorage,
} from "../utils/storage";
import {
  CHAT_MESSAGES_STORAGE_PREFIX,
  LETTER_MESSAGES_STORAGE_PREFIX,
} from "../../hooks/useMessages";

export const DEVICE_PRIVACY_STORAGE_KEY = "device_privacy";
export const PUBLIC_DEVICE_IDLE_MS = 5 * 60 * 1000;
export const SHUTDOWN_SECONDS = 120;
const IDLE_CHECK_INTERVAL_MS = 1000;

type DevicePrivacy = "private" | "public";

function readDevicePrivacy(): DevicePrivacy | null {
  const stored = readSessionStorage(DEVICE_PRIVACY_STORAGE_KEY);
  return stored === "private" || stored === "public" ? stored : null;
}

/**
 * Removes the sessionStorage keys this app is known to write, rather than
 * clearing all of sessionStorage, so unrelated data isn't touched.
 */
function clearKnownSessionStorage() {
  removeSessionStorage(DEVICE_PRIVACY_STORAGE_KEY);
  removeSessionStorageByPrefix(CHAT_MESSAGES_STORAGE_PREFIX);
  removeSessionStorageByPrefix(LETTER_MESSAGES_STORAGE_PREFIX);
}

interface Props {
  children: React.ReactNode;
}

/**
 * Requires a device privacy choice before rendering sensitive pages and, on a
 * public device, clears the session after an inactivity warning expires.
 */
export default function DevicePrivacyGuard({ children }: Props) {
  const [devicePrivacy, setDevicePrivacy] = useState<DevicePrivacy | null>(
    readDevicePrivacy,
  );
  const [shutdownDeadline, setShutdownDeadline] = useState<number | null>(null);
  const [secondsRemaining, setSecondsRemaining] = useState(SHUTDOWN_SECONDS);
  const lastActivityRef = useRef(Date.now());

  useEffect(() => {
    if (devicePrivacy !== "public" || shutdownDeadline !== null) return;

    const recordActivity = () => {
      lastActivityRef.current = Date.now();
    };

    const activityEvents: (keyof WindowEventMap)[] = [
      "click",
      "keydown",
      "mousemove",
      "scroll",
      "touchstart",
    ];
    activityEvents.forEach((event) =>
      window.addEventListener(event, recordActivity, { passive: true }),
    );
    recordActivity();

    const idleCheckTimer = window.setInterval(() => {
      if (Date.now() - lastActivityRef.current >= PUBLIC_DEVICE_IDLE_MS) {
        setShutdownDeadline(Date.now() + SHUTDOWN_SECONDS * 1000);
        setSecondsRemaining(SHUTDOWN_SECONDS);
      }
    }, IDLE_CHECK_INTERVAL_MS);

    return () => {
      activityEvents.forEach((event) =>
        window.removeEventListener(event, recordActivity),
      );
      window.clearInterval(idleCheckTimer);
    };
  }, [devicePrivacy, shutdownDeadline]);

  useEffect(() => {
    if (shutdownDeadline === null) return;

    const updateCountdown = () => {
      const remaining = Math.max(
        0,
        Math.ceil((shutdownDeadline - Date.now()) / 1000),
      );
      setSecondsRemaining(remaining);

      if (remaining === 0) {
        window.clearInterval(countdownTimer);
        clearKnownSessionStorage();
        window.close();
        // Browsers only permit scripts to close tabs that scripts opened.
        // Redirect away from sensitive content when closing is blocked.
        window.location.replace("/");
      }
    };

    const countdownTimer = window.setInterval(updateCountdown, 250);
    updateCountdown();
    return () => window.clearInterval(countdownTimer);
  }, [shutdownDeadline]);

  function selectDevice(value: DevicePrivacy) {
    writeSessionStorage(DEVICE_PRIVACY_STORAGE_KEY, value);
    setDevicePrivacy(value);
  }

  function cancelShutdown() {
    setShutdownDeadline(null);
    setSecondsRemaining(SHUTDOWN_SECONDS);
  }

  if (devicePrivacy === null) {
    return (
      <Modal title="Is this a public or private device?" dismissible={false}>
        <p className="mb-5 text-gray-dark">
          Choose public if other people can access this device. We will use your
          answer to help protect your conversation history.
        </p>
        <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={() => selectDevice("public")}
            className="border border-green-dark text-green-dark hover:bg-green-light"
          >
            Public device
          </button>
          <button
            type="button"
            onClick={() => selectDevice("private")}
            className="bg-green-dark text-white hover:bg-green-medium"
          >
            Private device
          </button>
        </div>
      </Modal>
    );
  }

  return (
    <>
      <div className="contents" inert={shutdownDeadline !== null}>
        {children}
      </div>
      {shutdownDeadline !== null && (
        <Modal title="Are you still there?" onClose={cancelShutdown}>
          <p className="mb-5 text-gray-dark" aria-live="polite">
            If you do nothing, this page will close in {secondsRemaining}{" "}
            {secondsRemaining === 1 ? "second" : "seconds"}, clearing all
            message history.
          </p>
          <div className="flex justify-end">
            <button
              type="button"
              onClick={cancelShutdown}
              className="bg-green-dark text-white hover:bg-green-medium"
            >
              Cancel
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}

interface ModalProps {
  children: React.ReactNode;
  title: string;
  /** When false, Escape cannot dismiss the dialog; only an explicit choice can. */
  dismissible?: boolean;
  onClose?: () => void;
}


function Modal({ children, title, dismissible = true, onClose }: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    dialogRef.current?.showModal();
  }, []);

  return (
    <dialog
      ref={dialogRef}
      onCancel={(event) => {
        if (!dismissible) event.preventDefault();
      }}
      onClose={onClose}
      aria-labelledby="device-privacy-dialog-title"
      className="fixed top-1/2 left-1/2 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-lg border-none bg-white p-6 shadow-xl backdrop:bg-black/50"
    >
      <h2 id="device-privacy-dialog-title" className="mb-3 text-xl font-bold">
        {title}
      </h2>
      {children}
    </dialog>
  );
}
