import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import AutoExpandText from "../../pages/Chat/components/AutoExpandText";

describe("AutoExpandText", () => {
  it("renders children", () => {
    render(<AutoExpandText isExpanded={true}>hello</AutoExpandText>);
    expect(screen.getByText("hello")).toBeInTheDocument();
  });

  it("applies expanded classes when isExpanded is true", () => {
    const { container } = render(
      <AutoExpandText isExpanded={true}>content</AutoExpandText>,
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("grid-rows-[1fr]");
    expect(wrapper.className).not.toContain("opacity-0");
  });

  it("applies collapsed classes when isExpanded is false", () => {
    const { container } = render(
      <AutoExpandText isExpanded={false}>content</AutoExpandText>,
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("grid-rows-[0fr]");
    expect(wrapper.className).toContain("opacity-0");
  });
});
