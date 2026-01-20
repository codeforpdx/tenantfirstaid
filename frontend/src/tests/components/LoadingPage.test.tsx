import { render, screen } from "@testing-library/react";
import LoadingPage from "../../pages/LoadingPage";

describe("LoadingPage", () => {
  it("renders loading spinner and text", () => {
    render(<LoadingPage />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });
});
