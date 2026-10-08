import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import LetterGenerationDialog from "../../pages/Letter/components/LetterGenerationDialog";

const renderDialog = (isRedirected: boolean) => {
  render(
    <LetterGenerationDialog
      ref={{ current: null }}
      isRedirected={isRedirected}
    />,
  );
  return screen.getByText(/It'll take a few seconds/, { selector: "p" });
};

describe("LetterGenerationDialog", () => {
  it("omits the redirect notice when not redirected", () => {
    expect(renderDialog(false).textContent).not.toMatch(/redirected/);
  });

  it("shows the redirect notice when redirected", () => {
    expect(renderDialog(true).textContent).toMatch(/redirected/);
  });
});
