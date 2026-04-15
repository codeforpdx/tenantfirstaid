import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { HumanMessage } from "@langchain/core/messages";
import ExportMessagesButton from "../../pages/Chat/components/ExportMessagesButton";

vi.mock("../../pages/Chat/utils/exportHelper", () => ({
  default: vi.fn(),
}));

import exportMessages from "../../pages/Chat/utils/exportHelper";

describe("ExportMessagesButton", () => {
  it("renders an Export button", () => {
    render(<ExportMessagesButton messages={[]} />);
    expect(screen.getByRole("button", { name: "Export" })).toBeInTheDocument();
  });

  it("calls exportMessages with the provided messages on click", () => {
    const messages = [new HumanMessage({ content: "hello", id: "1" })];
    render(<ExportMessagesButton messages={messages} />);

    fireEvent.click(screen.getByRole("button", { name: "Export" }));

    expect(exportMessages).toHaveBeenCalledWith(messages);
  });
});
