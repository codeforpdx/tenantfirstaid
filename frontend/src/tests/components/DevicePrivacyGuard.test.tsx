import { act, fireEvent, render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
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

function renderGuard(path = "/chat") {
  const router = createMemoryRouter(
    [
      {
        path: "*",
        element: (
          <DevicePrivacyGuard>
            <div>Sensitive page</div>
          </DevicePrivacyGuard>
        ),
      },
    ],
    { initialEntries: [path] },
  );
  render(<RouterProvider router={router} />);
  return router;
}

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
    vi.restoreAllMocks();
  });

  it("stores the initial private-device choice and displays the page", () => {
    renderGuard();

    expect(screen.queryByText("Sensitive page")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Private device" }));

    expect(sessionStorage.getItem(DEVICE_PRIVACY_STORAGE_KEY)).toBe("private");
    expect(screen.getByText("Sensitive page")).toBeInTheDocument();
  });

  it.each([
    "/",
    "/about",
    "/privacy-policy",
    "/referrals",
    "/disclaimer",
    "/chatbot",
    "/letterhead",
  ])("shows %s without a choice or idle clearing", (path) => {
    vi.useFakeTimers();
    const closeSpy = vi.spyOn(window, "close").mockImplementation(() => {});
    sessionStorage.setItem("chat_messages:portland", "chat history");
    renderGuard(path);

    expect(screen.getByText("Sensitive page")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    act(() => vi.advanceTimersByTime(PUBLIC_DEVICE_IDLE_MS));
    act(() => vi.advanceTimersByTime(SHUTDOWN_SECONDS * 1000));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(sessionStorage.getItem(DEVICE_PRIVACY_STORAGE_KEY)).toBeNull();
    expect(sessionStorage.getItem("chat_messages:portland")).toBe(
      "chat history",
    );
    expect(closeSpy).not.toHaveBeenCalled();
  });

  it.each([
    "/chat",
    "/chat/",
    "/chat/oregon/portland",
    "/letter",
    "/letter/",
    "/letter/oregon/portland",
    "/CHAT",
  ])("requires a choice before displaying %s", (path) => {
    renderGuard(path);

    expect(screen.getByRole("dialog")).toHaveAccessibleName(
      "Is this a public or private device?",
    );
    expect(screen.queryByText("Sensitive page")).not.toBeInTheDocument();
  });

  it("prompts when navigating from the home page to chat", async () => {
    const router = renderGuard("/");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await act(async () => {
      await router.navigate("/chat");
    });

    expect(screen.getByRole("dialog")).toHaveAccessibleName(
      "Is this a public or private device?",
    );
    expect(screen.queryByText("Sensitive page")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Private device" }));
    expect(screen.getByText("Sensitive page")).toBeInTheDocument();
  });

  it("starts public-device idle tracking only after a choice", async () => {
    vi.useFakeTimers();
    const router = renderGuard("/");
    act(() => vi.advanceTimersByTime(PUBLIC_DEVICE_IDLE_MS * 2));

    await act(async () => {
      await router.navigate("/chat");
    });
    fireEvent.click(screen.getByRole("button", { name: "Public device" }));
    expect(sessionStorage.getItem(DEVICE_PRIVACY_STORAGE_KEY)).toBe("public");

    act(() => vi.advanceTimersByTime(PUBLIC_DEVICE_IDLE_MS - 1000));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    act(() => vi.advanceTimersByTime(1000));
    expect(screen.getByRole("dialog")).toHaveAccessibleName(
      "Are you still there?",
    );
  });

  it("preserves public-device idle tracking and clearing across navigation", async () => {
    vi.useFakeTimers();
    const closeSpy = vi.spyOn(window, "close").mockImplementation(() => {});
    sessionStorage.setItem(DEVICE_PRIVACY_STORAGE_KEY, "public");
    sessionStorage.setItem("chat_messages:portland", "chat history");
    sessionStorage.setItem("letter_messages:portland", "letter history");
    const router = renderGuard();

    act(() => vi.advanceTimersByTime(PUBLIC_DEVICE_IDLE_MS - 1000));
    // Navigate without an activity event so a click cannot reset the idle clock.
    await act(async () => {
      await router.navigate("/about");
    });
    expect(router.state.location.pathname).toBe("/about");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    act(() => vi.advanceTimersByTime(1000));
    expect(screen.getByRole("dialog")).toHaveAccessibleName(
      "Are you still there?",
    );
    act(() => vi.advanceTimersByTime(SHUTDOWN_SECONDS * 500));

    await act(async () => {
      await router.navigate("/referrals");
    });
    act(() => vi.advanceTimersByTime(SHUTDOWN_SECONDS * 500));

    expect(sessionStorage.getItem(DEVICE_PRIVACY_STORAGE_KEY)).toBeNull();
    expect(sessionStorage.getItem("chat_messages:portland")).toBeNull();
    expect(sessionStorage.getItem("letter_messages:portland")).toBeNull();
    expect(closeSpy).toHaveBeenCalledOnce();
  });

  it("warns after five idle minutes and cancel restarts inactivity tracking", () => {
    vi.useFakeTimers();
    sessionStorage.setItem(DEVICE_PRIVACY_STORAGE_KEY, "public");
    renderGuard();

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
    renderGuard();

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
    renderGuard();

    act(() => vi.advanceTimersByTime(PUBLIC_DEVICE_IDLE_MS));
    act(() => vi.advanceTimersByTime(SHUTDOWN_SECONDS * 1000));

    expect(sessionStorage.getItem(DEVICE_PRIVACY_STORAGE_KEY)).toBeNull();
    expect(sessionStorage.getItem("chat_messages:portland")).toBeNull();
    expect(sessionStorage.getItem("letter_messages:portland")).toBeNull();
    expect(sessionStorage.getItem("unrelated")).toBe("keep me");
    expect(closeSpy).toHaveBeenCalledOnce();
  });
});
