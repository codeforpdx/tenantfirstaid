/// <reference types="@testing-library/jest-dom" />
import "@testing-library/jest-dom/vitest";

// jsdom doesn't implement matchMedia; MobilePanel uses it to resync open state
// across the lg breakpoint. Provide a minimal stub so component tests render.
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });
}

// jsdom implements neither element scrolling nor modal dialogs; stub them so
// components that call these on mount render. Tests may override them.
if (typeof window !== "undefined") {
  HTMLElement.prototype.scrollTo ??= () => {};
  HTMLDialogElement.prototype.showModal ??= () => {};
  HTMLDialogElement.prototype.close ??= () => {};
}
