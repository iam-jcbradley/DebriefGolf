import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { Select } from "./select";

describe("Select", () => {
  it("renders options and reflects a chosen value", async () => {
    const user = userEvent.setup();
    render(
      <Select aria-label="Club">
        <option value="driver">Driver</option>
        <option value="putter">Putter</option>
      </Select>
    );

    const select = screen.getByLabelText("Club");
    await user.selectOptions(select, "putter");

    expect(select).toHaveValue("putter");
  });

  it("forwards standard select props like disabled", () => {
    render(
      <Select aria-label="Lie" disabled>
        <option value="fairway">Fairway</option>
      </Select>
    );
    expect(screen.getByLabelText("Lie")).toBeDisabled();
  });
});
