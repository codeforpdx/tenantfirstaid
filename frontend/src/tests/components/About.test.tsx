import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import About from "../../About";
import { MemoryRouter } from "react-router-dom";

describe("About component", () => {
  beforeEach(() => {
    render(
      <MemoryRouter>
        <About />
      </MemoryRouter>,
    );
  });

  it("renders without crashing", () => {
    expect(screen.getByText("About Tenant First Aid")).toBeInTheDocument();
  });

  it("displays legal disclaimer section", () => {
    expect(
      screen.getByText("Legal Disclaimer & Privacy Notice"),
    ).toBeInTheDocument();
  });

  it("displays contact information", () => {
    expect(screen.getByText("michael@qiu-qiulaw.com")).toBeInTheDocument();
  });
});
