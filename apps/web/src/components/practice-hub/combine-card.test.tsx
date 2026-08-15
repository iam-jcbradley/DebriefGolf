import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Combine, WeaknessSignal } from "@/lib/api";
import { CombineCard } from "./combine-card";

const combine: Combine = {
  weakness: "iron_strike_quality",
  name: "Low-Point Compression",
  instructions: "Hit 10 balls off a towel.",
  target_metric: "Smash factor >1.36",
  video_search_url: "https://example.com/search",
};

const signal: WeaknessSignal = {
  weakness: "iron_strike_quality",
  detail: "Average iron smash factor is 1.20 over 6 shots.",
};

describe("CombineCard", () => {
  it("renders the combine name, detail, and target metric", () => {
    render(<CombineCard combine={combine} signal={signal} />);
    expect(screen.getByText("Low-Point Compression")).toBeInTheDocument();
    expect(screen.getByText(signal.detail)).toBeInTheDocument();
    expect(screen.getByText("Smash factor >1.36")).toBeInTheDocument();
  });

  it("links to the curated video search", () => {
    render(<CombineCard combine={combine} signal={signal} />);
    const link = screen.getByRole("link", { name: /watch tutorials/i });
    expect(link).toHaveAttribute("href", combine.video_search_url);
  });
});
