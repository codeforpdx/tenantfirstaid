import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { createRef } from "react";
import LetterGenerationDialog from "../../pages/Letter/components/LetterGenerationDialog";

function renderDialog(path: string) {
  const ref = createRef<HTMLDialogElement>();
  render(
    <MemoryRouter initialEntries={[path]}>
      <LetterGenerationDialog ref={ref} />
    </MemoryRouter>,
  );
}

describe("LetterGenerationDialog", () => {
  it("shows redirect message when path is not /letter", () => {
    renderDialog("/letter/some-org");

    expect(
      screen.getByText(/you've been redirected here/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/go back to your previous page/i),
    ).toBeInTheDocument();
  });

  it("does not show redirect message on /letter path", () => {
    renderDialog("/letter");

    expect(
      screen.queryByText(/you've been redirected here/i),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/go back to your previous page/i),
    ).not.toBeInTheDocument();
  });

  it("always shows the generation notice text", () => {
    renderDialog("/letter");

    expect(
      screen.getByText(/take a few seconds to complete/i),
    ).toBeInTheDocument();
  });

  it("renders a Close button", () => {
    renderDialog("/letter");
    expect(
      screen.getByRole("button", { name: "close-dialog", hidden: true }),
    ).toBeInTheDocument();
  });

  it("calls dialog.close() when Close is clicked", () => {
    renderDialog("/letter");

    const dialog = screen.getByRole("dialog", { hidden: true });
    const closeSpy = vi.fn();
    Object.defineProperty(dialog, "close", { value: closeSpy });

    fireEvent.click(
      screen.getByRole("button", { name: "close-dialog", hidden: true }),
    );

    expect(closeSpy).toHaveBeenCalled();
  });
});
