import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MembershipCard } from "./membership-card";

describe("MembershipCard", () => {
  it("renders the member's name and handicap index", () => {
    render(<MembershipCard name="Jamie Bradley" handicapIndex={5.4} />);
    expect(screen.getByText("Jamie Bradley")).toBeInTheDocument();
    expect(screen.getByText("5.4")).toBeInTheDocument();
  });

  it("renders an em dash when handicap index is null", () => {
    render(<MembershipCard name="Jamie Bradley" handicapIndex={null} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("derives two-letter initials from a full name", () => {
    render(<MembershipCard name="Jamie Bradley" handicapIndex={5.4} />);
    expect(screen.getByText("JB")).toBeInTheDocument();
  });

  it("falls back to the app name when no club is given", () => {
    render(<MembershipCard name="Jamie Bradley" handicapIndex={5.4} />);
    expect(screen.getByText("Debrief Golf")).toBeInTheDocument();
  });

  it("shows the given club instead of the fallback", () => {
    render(<MembershipCard name="Jamie Bradley" handicapIndex={5.4} club="Pawleys Creek GC" />);
    expect(screen.getByText("Pawleys Creek GC")).toBeInTheDocument();
    expect(screen.queryByText("Debrief Golf")).not.toBeInTheDocument();
  });

  it("shows member-since text only when provided", () => {
    const { rerender } = render(<MembershipCard name="Jamie Bradley" handicapIndex={5.4} />);
    expect(screen.queryByText(/Member since/)).not.toBeInTheDocument();

    rerender(<MembershipCard name="Jamie Bradley" handicapIndex={5.4} memberSince="2024" />);
    expect(screen.getByText("Member since 2024")).toBeInTheDocument();
  });
});
