import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import InitializationForm from "../../pages/Chat/components/InitializationForm";
import HousingContextProvider from "../../contexts/HousingContext";
import { BrowserRouter } from "react-router-dom";

vi.mock("../../pages/Chat/utils/streamHelper", () => ({
  streamText: vi.fn(),
}));

const renderInitializationForm = () => {
  render(
    <BrowserRouter>
      <HousingContextProvider>
        <InitializationForm addMessage={vi.fn()} setMessages={vi.fn()} />
      </HousingContextProvider>
    </BrowserRouter>,
  );
};

describe("InitializationForm", () => {
  it("renders all form fields", () => {
    renderInitializationForm();

    const citySelect = screen.getByLabelText("city");
    const housingSelect = screen.getByLabelText("housing type");
    const topicSelect = screen.getByLabelText("tenant topic");
    const issueInput = screen.getByPlaceholderText(
      /briefly describe your specific/i,
    );
    const chatButton = screen.getByRole("button", { name: "enter chat" });

    expect(citySelect).toBeInTheDocument();
    expect(housingSelect).toBeInTheDocument();
    expect(topicSelect).toBeInTheDocument();
    expect(issueInput).toBeInTheDocument();
    expect(chatButton).toBeInTheDocument();
  });

  it('disables submit when city is "other"', async () => {
    renderInitializationForm();

    const citySelect = screen.getByLabelText("city");
    const chatButton = screen.getByRole("button", { name: "enter chat" });

    expect(chatButton).not.toBeDisabled();

    fireEvent.change(citySelect, { target: { value: "other" } });

    await waitFor(() => {
      expect(chatButton).toBeDisabled();
    });
  });

  it("updates context on field changes", async () => {
    renderInitializationForm();

    const citySelect = screen.getByLabelText("city");
    const housingSelect = screen.getByLabelText("housing type");
    const topicSelect = screen.getByLabelText("tenant topic");
    const issueInput = screen.getByPlaceholderText(
      /briefly describe your specific/i,
    );

    fireEvent.change(citySelect, { target: { value: "portland" } });
    await waitFor(() => {
      expect(citySelect).toHaveValue("portland");
    });

    fireEvent.change(housingSelect, {
      target: { value: "Apartment/House Rental" },
    });
    await waitFor(() => {
      expect(housingSelect).toHaveValue("Apartment/House Rental");
    });

    fireEvent.change(topicSelect, { target: { value: "Rent Issues" } });
    await waitFor(() => {
      expect(topicSelect).toHaveValue("Rent Issues");
    });

    fireEvent.change(issueInput, {
      target: { value: "My landlord won't repair the heat" },
    });
    await waitFor(() => {
      expect(issueInput).toHaveValue("My landlord won't repair the heat");
    });
  });

  it("shows/hides Generate Letter button correctly", async () => {
    renderInitializationForm();

    const citySelect = screen.getByLabelText("city");
    const housingSelect = screen.getByLabelText("housing type");
    const topicSelect = screen.getByLabelText("tenant topic");
    const issueInput = screen.getByPlaceholderText(
      /briefly describe your specific/i,
    );

    // Hides generate letter by default
    expect(
      screen.queryByRole("link", { name: "generate letter" }),
    ).not.toBeInTheDocument();

    fireEvent.change(citySelect, { target: { value: "portland" } });
    fireEvent.change(housingSelect, {
      target: { value: "Apartment/House Rental" },
    });
    fireEvent.change(topicSelect, { target: { value: "Rent Issues" } });
    fireEvent.change(issueInput, {
      target: { value: "My landlord won't repair the heat" },
    });

    await waitFor(() => {
      expect(
        screen.queryByRole("link", { name: "generate letter" }),
      ).toBeInTheDocument();
    });

    // Hides generate letter for Eviction and Notices
    fireEvent.change(topicSelect, {
      target: { value: "Eviction and Notices" },
    });

    await waitFor(() => {
      expect(
        screen.queryByRole("link", { name: "generate letter" }),
      ).not.toBeInTheDocument();
    });

    fireEvent.change(topicSelect, { target: { value: "Rent Issues" } });

    await waitFor(() => {
      expect(
        screen.queryByRole("link", { name: "generate letter" }),
      ).toBeInTheDocument();
    });

    fireEvent.change(citySelect, { target: { value: "other" } });

    // Changes styling for generate button when other is selected
    await waitFor(() => {
      expect(screen.getByRole("link", { name: "generate letter" })).toHaveClass(
        "opacity-50",
      );
    });
  });
});
