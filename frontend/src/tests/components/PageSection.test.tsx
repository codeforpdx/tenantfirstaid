import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import PageSection from "../../shared/components/PageSection";

describe("PageSection", () => {
  it.each([
    { level: 2, sizeClass: "text-2xl" },
    { level: 3, sizeClass: "text-xl" },
  ] as const)(
    "renders h$level heading with correct styling",
    ({ level, sizeClass }) => {
      render(
        <PageSection title="Test Heading" headingLevel={level}>
          <p>Test content</p>
        </PageSection>,
      );

      const heading = screen.getByRole("heading", {
        level,
        name: "Test Heading",
      });
      expect(heading).toBeInTheDocument();
      expect(heading).toHaveClass(sizeClass);
    },
  );

  it("renders children and applies custom className", () => {
    const { container } = render(
      <PageSection
        title="Test"
        headingLevel={2}
        className="space-y-6 custom-class"
      >
        <p>Child paragraph</p>
        <span>Child span</span>
      </PageSection>,
    );

    expect(screen.getByText("Child paragraph")).toBeInTheDocument();
    expect(screen.getByText("Child span")).toBeInTheDocument();

    const wrapper = container.querySelector(".space-y-6.custom-class");
    expect(wrapper).toBeInTheDocument();
  });

  it("renders JSX title", () => {
    render(
      <PageSection
        title={
          <>
            Line 1<br />
            Line 2
          </>
        }
        headingLevel={2}
      >
        <p>Content</p>
      </PageSection>,
    );

    const heading = screen.getByRole("heading", { level: 2 });
    expect(heading).toHaveTextContent("Line 1Line 2");
  });
});
