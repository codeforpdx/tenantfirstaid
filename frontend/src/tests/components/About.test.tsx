import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import About from "../../About";
import { MemoryRouter } from "react-router";

describe("About component", () => {
  it("renders without crashing", () => {
    render(
      <MemoryRouter>
        <About />
      </MemoryRouter>,
    );
    expect(screen.getByText("About Tenant First Aid")).toBeInTheDocument();
  });

  it("displays legal disclaimer section", () => {
    render(
      <MemoryRouter>
        <About />
      </MemoryRouter>,
    );
    expect(
      screen.getByText("Legal Disclaimer & Privacy Notice"),
    ).toBeInTheDocument();
  });

  it("displays contact information", () => {
    render(
      <MemoryRouter>
        <About />
      </MemoryRouter>,
    );
    expect(screen.getByText("michael@qiu-qiulaw.com")).toBeInTheDocument();
  });
});
