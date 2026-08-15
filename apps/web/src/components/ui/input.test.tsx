import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { Input } from "./input";

describe("Input", () => {
  it("renders and accepts typed input", async () => {
    const user = userEvent.setup();
    render(<Input aria-label="Course name" />);

    const input = screen.getByLabelText("Course name");
    await user.type(input, "Pawleys Creek");

    expect(input).toHaveValue("Pawleys Creek");
  });

  it("forwards standard input props like placeholder and disabled", () => {
    render(<Input aria-label="Notes" placeholder="Add a note" disabled />);
    const input = screen.getByLabelText("Notes");
    expect(input).toHaveAttribute("placeholder", "Add a note");
    expect(input).toBeDisabled();
  });
});
