import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SuckerPinAlert } from "./sucker-pin-alert";

describe("SuckerPinAlert", () => {
  it("names the club whose dispersion pattern covers the pin", () => {
    render(<SuckerPinAlert club="7-Iron" />);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Sucker pin");
    expect(alert).toHaveTextContent("7-Iron");
  });
});
