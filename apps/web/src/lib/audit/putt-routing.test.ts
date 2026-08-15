import { describe, expect, it } from "vitest";
import {
  LONG_PUTT_THRESHOLD_YARDS,
  SHORT_PUTT_THRESHOLD_YARDS,
  needsFringeIsolationPrompt,
  resolveFringeIsolation,
  routePutt,
} from "./putt-routing";

describe("routePutt", () => {
  it("routes putts under 6ft to short_putt", () => {
    expect(routePutt(0.5)).toBe("short_putt");
    expect(routePutt(SHORT_PUTT_THRESHOLD_YARDS - 0.01)).toBe("short_putt");
  });

  it("routes putts over 20ft to long_putt", () => {
    expect(routePutt(LONG_PUTT_THRESHOLD_YARDS + 0.01)).toBe("long_putt");
    expect(routePutt(30)).toBe("long_putt");
  });

  it("routes putts between 6ft and 20ft to mid_putt", () => {
    expect(routePutt(SHORT_PUTT_THRESHOLD_YARDS)).toBe("mid_putt");
    expect(routePutt(LONG_PUTT_THRESHOLD_YARDS)).toBe("mid_putt");
    expect(routePutt(5)).toBe("mid_putt");
  });
});

describe("needsFringeIsolationPrompt", () => {
  it("prompts when a putter is used from the fringe", () => {
    expect(needsFringeIsolationPrompt("Putter", "fringe")).toBe(true);
  });

  it("prompts when a putter is used from any non-green lie", () => {
    expect(needsFringeIsolationPrompt("Putter", "rough")).toBe(true);
  });

  it("does not prompt when a putter is used from the green", () => {
    expect(needsFringeIsolationPrompt("Putter", "green")).toBe(false);
  });

  it("does not prompt for a non-putter club", () => {
    expect(needsFringeIsolationPrompt("SW", "fringe")).toBe(false);
  });

  it("does not prompt when there's no club recorded", () => {
    expect(needsFringeIsolationPrompt(null, "fringe")).toBe(false);
  });
});

describe("resolveFringeIsolation", () => {
  it("reclassifies to green when counted as a true putt", () => {
    expect(resolveFringeIsolation("true_putt", "fringe")).toBe("green");
  });

  it("keeps the original lie when counted as short game", () => {
    expect(resolveFringeIsolation("fringe_short_game", "fringe")).toBe("fringe");
    expect(resolveFringeIsolation("fringe_short_game", "rough")).toBe("rough");
  });
});
