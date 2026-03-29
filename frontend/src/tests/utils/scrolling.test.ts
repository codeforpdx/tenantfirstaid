import { describe, it, expect, vi, afterEach } from "vitest";
import { scrollToTop } from "../../shared/utils/scrolling";

describe("scrollToTop", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("calls window.scrollTo with top: 0 and smooth behavior", () => {
    const scrollToSpy = vi
      .spyOn(window, "scrollTo")
      .mockImplementation(() => {});

    scrollToTop();

    expect(scrollToSpy).toHaveBeenCalledWith({ top: 0, behavior: "smooth" });
  });
});
