import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "./card";

describe("Card", () => {
  it("renders composed content", () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Round Summary</CardTitle>
          <CardDescription>Pawleys Creek GC — August 15</CardDescription>
        </CardHeader>
        <CardContent>78 (+6)</CardContent>
        <CardFooter>Round logged.</CardFooter>
      </Card>
    );

    expect(screen.getByText("Round Summary")).toBeInTheDocument();
    expect(screen.getByText("Pawleys Creek GC — August 15")).toBeInTheDocument();
    expect(screen.getByText("78 (+6)")).toBeInTheDocument();
    expect(screen.getByText("Round logged.")).toBeInTheDocument();
  });

  it("renders the title as a heading element", () => {
    render(<CardTitle>Round Summary</CardTitle>);
    expect(screen.getByRole("heading", { name: "Round Summary" })).toBeInTheDocument();
  });
});
