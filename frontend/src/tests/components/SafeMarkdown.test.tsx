import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import SafeMarkdown from "../../shared/components/SafeMarkdown";

describe("SafeMarkdown", () => {
  it("renders links that open in a new tab with rel=noopener noreferrer", () => {
    render(
      <SafeMarkdown>
        {"[Oregon tenant rights](https://example.com)"}
      </SafeMarkdown>,
    );

    const link = screen.getByRole("link", { name: "Oregon tenant rights" });
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(link).toHaveAttribute("href", "https://example.com");
  });

  it("renders paragraphs with bottom margin class", () => {
    render(<SafeMarkdown>{"Hello world"}</SafeMarkdown>);
    const p = screen.getByText("Hello world").closest("p");
    expect(p).toHaveClass("mb-3");
  });

  it("renders unordered lists with disc style", () => {
    render(<SafeMarkdown>{"- item one\n- item two"}</SafeMarkdown>);

    const list = screen.getByRole("list");
    expect(list.tagName).toBe("UL");
    expect(list).toHaveClass("list-disc");
    expect(screen.getByText("item one")).toBeInTheDocument();
    expect(screen.getByText("item two")).toBeInTheDocument();
  });

  it("renders ordered lists with decimal style", () => {
    render(<SafeMarkdown>{"1. first\n2. second"}</SafeMarkdown>);

    const list = screen.getByRole("list");
    expect(list.tagName).toBe("OL");
    expect(list).toHaveClass("list-decimal");
    expect(screen.getByText("first")).toBeInTheDocument();
    expect(screen.getByText("second")).toBeInTheDocument();
  });
});
