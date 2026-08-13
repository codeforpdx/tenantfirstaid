import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import DevicePrivacyGuard, {
  DEVICE_PRIVACY_STORAGE_KEY,
  PUBLIC_DEVICE_IDLE_MS,
  SHUTDOWN_SECONDS,
} from "../../shared/components/DevicePrivacyGuard";

describe("DevicePrivacyGuard", () => {
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
});
