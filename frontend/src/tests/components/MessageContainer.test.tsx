import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import MessageContainer from "../../shared/components/MessageContainer";

describe("MessageContainer", () => {
  it("does not show the letter panel when letterContent is empty", () => {
    render(
      <MessageContainer isOngoing={false} letterContent="">
        <span>chat</span>
      </MessageContainer>,
    );

    expect(screen.queryByText("Dear Landlord")).toBeNull();
  });

  it("shows the letter panel when letterContent is non-empty", () => {
    render(
      <MessageContainer
        isOngoing={false}
        letterContent="Dear Landlord, please fix the heat."
      >
        <span>chat</span>
      </MessageContainer>,
    );

    expect(
      screen.getByText("Dear Landlord, please fix the heat."),
    ).toBeInTheDocument();
  });
});
