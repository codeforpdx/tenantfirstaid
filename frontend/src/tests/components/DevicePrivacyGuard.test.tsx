import { act, fireEvent, render, screen } from "@testing-library/react";
import {
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";
import DevicePrivacyGuard, {
  DEVICE_PRIVACY_STORAGE_KEY,
  PUBLIC_DEVICE_IDLE_MS,
  SHUTDOWN_SECONDS,
} from "../../shared/components/DevicePrivacyGuard";

describe("DevicePrivacyGuard", () => {
  beforeAll(() => {
    HTMLDialogElement.prototype.showModal = vi.fn(function (
      this: HTMLDialogElement,
    ) {
      this.setAttribute("open", "");
    });
    HTMLDialogElement.prototype.close = vi.fn(function (
      this: HTMLDialogElement,
    ) {
      this.removeAttribute("open");
      this.dispatchEvent(new Event("close"));
    });
  });

  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("stores the initial private-device choice and displays the page", () => {
    render(
      <DevicePrivacyGuard>
        <div>Sensitive page</div>
      </DevicePrivacyGuard>,
    );

    expect(screen.queryByText("Sensitive page")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Private device" }));

    expect(sessionStorage.getItem(DEVICE_PRIVACY_STORAGE_KEY)).toBe("private");
    expect(screen.getByText("Sensitive page")).toBeInTheDocument();
  });

  it("warns after five idle minutes and cancel restarts inactivity tracking", () => {
    vi.useFakeTimers();
    sessionStorage.setItem(DEVICE_PRIVACY_STORAGE_KEY, "public");
    render(
      <DevicePrivacyGuard>
        <div>Sensitive page</div>
      </DevicePrivacyGuard>,
    );

    act(() => vi.advanceTimersByTime(PUBLIC_DEVICE_IDLE_MS));
    expect(screen.getByRole("dialog")).toHaveTextContent(
      `close in ${SHUTDOWN_SECONDS} seconds`,
    );

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    act(() => vi.advanceTimersByTime(PUBLIC_DEVICE_IDLE_MS));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("resets the public-device inactivity timer when the user is active", () => {
    vi.useFakeTimers();
    sessionStorage.setItem(DEVICE_PRIVACY_STORAGE_KEY, "public");
    render(
      <DevicePrivacyGuard>
        <div>Sensitive page</div>
      </DevicePrivacyGuard>,
    );

    act(() => vi.advanceTimersByTime(PUBLIC_DEVICE_IDLE_MS - 1000));
    fireEvent.keyDown(window, { key: "Tab" });
    act(() => vi.advanceTimersByTime(1000));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("removes message history and closes the page when the warning expires", () => {
    vi.useFakeTimers();
    const closeSpy = vi.spyOn(window, "close").mockImplementation(() => {});
    sessionStorage.setItem(DEVICE_PRIVACY_STORAGE_KEY, "public");
    sessionStorage.setItem("chat_messages:portland", "chat history");
    sessionStorage.setItem("letter_messages:portland", "letter history");
    sessionStorage.setItem("unrelated", "keep me");
    render(
      <DevicePrivacyGuard>
        <div>Sensitive page</div>
      </DevicePrivacyGuard>,
    );

    act(() => vi.advanceTimersByTime(PUBLIC_DEVICE_IDLE_MS));
    act(() => vi.advanceTimersByTime(SHUTDOWN_SECONDS * 1000));

    expect(sessionStorage.getItem(DEVICE_PRIVACY_STORAGE_KEY)).toBeNull();
    expect(sessionStorage.getItem("chat_messages:portland")).toBeNull();
    expect(sessionStorage.getItem("letter_messages:portland")).toBeNull();
    expect(sessionStorage.getItem("unrelated")).toBe("keep me");
    expect(closeSpy).toHaveBeenCalledOnce();
  });
});
