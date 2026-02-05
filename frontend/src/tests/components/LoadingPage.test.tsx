import { render, screen } from "@testing-library/react";
import LoadingPage from "../../pages/LoadingPage";

describe("LoadingPage", () => {
  it("renders loading spinner and text", () => {
    const { container } = render(<LoadingPage />);

    expect(screen.getByText("Loading...")).toBeInTheDocument();
    const spinner = container.querySelector(".animate-spin");
    expect(spinner).toBeInTheDocument();
  });
});
