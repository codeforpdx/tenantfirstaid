import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import SelectField from "../../pages/Chat/components/SelectField";

describe("SelectField", () => {
  const defaultProps = {
    name: "city",
    value: "",
    description: "Select a city",
    handleFunction: vi.fn(),
  };

  it("renders a label and select element", () => {
    render(
      <SelectField {...defaultProps}>
        <option value="portland">Portland</option>
      </SelectField>,
    );

    expect(screen.getByLabelText("city")).toBeInTheDocument();
    expect(screen.getByRole("combobox")).toBeInTheDocument();
  });

  it("renders a disabled placeholder option", () => {
    render(
      <SelectField {...defaultProps}>
        <option value="portland">Portland</option>
      </SelectField>,
    );

    const placeholder = screen.getByRole("option", { name: "Select a city" });
    expect(placeholder).toBeDisabled();
  });

  it("renders child options", () => {
    render(
      <SelectField {...defaultProps}>
        <option value="portland">Portland</option>
        <option value="eugene">Eugene</option>
      </SelectField>,
    );

    expect(
      screen.getByRole("option", { name: "Portland" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Eugene" })).toBeInTheDocument();
  });

  it("calls handleFunction with the selected value on change", () => {
    const handleFunction = vi.fn();
    render(
      <SelectField {...defaultProps} handleFunction={handleFunction}>
        <option value="portland">Portland</option>
      </SelectField>,
    );

    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "portland" },
    });

    expect(handleFunction).toHaveBeenCalledWith("portland");
  });

  it("reflects the controlled value", () => {
    render(
      <SelectField {...defaultProps} value="portland">
        <option value="portland">Portland</option>
      </SelectField>,
    );

    expect(screen.getByRole("combobox")).toHaveValue("portland");
  });
});
