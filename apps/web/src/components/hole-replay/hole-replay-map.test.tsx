import { act, render, screen, waitFor } from "@testing-library/react";
import mapboxgl from "mapbox-gl";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { HoleReplay } from "@/lib/api";
import { HoleReplayMap } from "./hole-replay-map";

// mapbox-gl's own CSS import chokes on this project's PostCSS config when
// pulled through Vitest's plain Vite pipeline (Next's build pipeline
// handles it fine — this is test-tooling friction, not an app bug).
vi.mock("mapbox-gl/dist/mapbox-gl.css", () => ({}));

vi.mock("mapbox-gl", () => {
  // A fresh instance per `new mapboxgl.Map()` call — sharing one instance
  // across tests would let a later test's assertions see an earlier
  // test's registered `on()` handlers.
  const MapMock = vi.fn(function MapMock() {
    return { on: vi.fn(), addSource: vi.fn(), addLayer: vi.fn(), remove: vi.fn() };
  });
  const MarkerMock = vi.fn(function MarkerMock() {
    return { setLngLat: vi.fn().mockReturnThis(), addTo: vi.fn().mockReturnThis() };
  });
  return { default: { accessToken: "", Map: MapMock, Marker: MarkerMock } };
});

const hole: HoleReplay = {
  round_id: 1,
  hole_number: 7,
  par: 4,
  yardage: 400,
  tee: { lat: 33.7, lng: -78.9 },
  green_center: { lat: 33.7025, lng: -78.9 },
  pin: null,
  green_boundary: null,
  shots: [],
  short_sided_count: 0,
};

// Markers resolve their color from CSS custom properties at runtime (see
// `resolveThemeColor` in hole-replay-map.tsx) rather than hardcoding hex —
// jsdom doesn't load globals.css, so these stand in for the real light-theme
// values it defines for --foreground/--primary/--status-good/--status-critical.
const THEME_FOREGROUND = "#211d17";
const THEME_PRIMARY = "#28402f";
const THEME_STATUS_GOOD = "#3f6b4a";
const THEME_STATUS_CRITICAL = "#9c4530";

beforeEach(() => {
  vi.mocked(mapboxgl.Map).mockClear();
  document.documentElement.style.setProperty("--foreground", THEME_FOREGROUND);
  document.documentElement.style.setProperty("--primary", THEME_PRIMARY);
  document.documentElement.style.setProperty("--status-good", THEME_STATUS_GOOD);
  document.documentElement.style.setProperty("--status-critical", THEME_STATUS_CRITICAL);
});

describe("HoleReplayMap", () => {
  it("falls back to the SVG schematic when no Mapbox token is configured", () => {
    render(<HoleReplayMap hole={hole} mapboxToken={undefined} />);

    expect(screen.getByText(/needs a Mapbox token/)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Hole 7 replay" })).toBeInTheDocument();
    expect(mapboxgl.Map).not.toHaveBeenCalled();
    expect(screen.queryByTestId("mapbox-container")).not.toBeInTheDocument();
  });

  it("renders the Mapbox container instead of the SVG when a token is configured", async () => {
    render(<HoleReplayMap hole={hole} mapboxToken="pk.test-token" />);

    expect(screen.getByTestId("mapbox-container")).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: "Hole 7 replay" })).not.toBeInTheDocument();
    // mapbox-gl loads via a dynamic import() (kept out of the no-token
    // bundle), so the mock resolves on a later microtask.
    await waitFor(() => expect(mapboxgl.Map).toHaveBeenCalledTimes(1));
  });

  it("falls back to the SVG schematic if the map reports an error", async () => {
    render(<HoleReplayMap hole={hole} mapboxToken="pk.test-token" />);

    await waitFor(() => expect(mapboxgl.Map).toHaveBeenCalledTimes(1));
    const mapInstance = vi.mocked(mapboxgl.Map).mock.results[0].value;
    const errorHandler = mapInstance.on.mock.calls.find(
      ([event]: [string]) => event === "error"
    )?.[1];
    expect(errorHandler).toBeDefined();

    act(() => {
      errorHandler({ error: { message: "network down" } });
    });

    expect(screen.getByRole("alert")).toHaveTextContent("network down");
    expect(screen.getByRole("img", { name: "Hole 7 replay" })).toBeInTheDocument();
  });

  it("does not place a pin marker when the hole has no recorded pin", async () => {
    render(<HoleReplayMap hole={hole} mapboxToken="pk.test-token" />);

    await waitFor(() => expect(mapboxgl.Map).toHaveBeenCalledTimes(1));
    const mapInstance = vi.mocked(mapboxgl.Map).mock.results[0].value;
    act(() => {
      mapInstance.on.mock.calls.find(([event]: [string]) => event === "load")?.[1]();
    });

    expect(mapboxgl.Marker).not.toHaveBeenCalledWith({ color: THEME_PRIMARY });
  });

  it("places a distinct pin marker when the hole has a recorded pin", async () => {
    render(
      <HoleReplayMap
        hole={{ ...hole, pin: { lat: 33.7026, lng: -78.9001 } }}
        mapboxToken="pk.test-token"
      />
    );

    await waitFor(() => expect(mapboxgl.Map).toHaveBeenCalledTimes(1));
    const mapInstance = vi.mocked(mapboxgl.Map).mock.results[0].value;
    act(() => {
      mapInstance.on.mock.calls.find(([event]: [string]) => event === "load")?.[1]();
    });

    expect(mapboxgl.Marker).toHaveBeenCalledWith({ color: THEME_PRIMARY });
    const pinMarker = vi
      .mocked(mapboxgl.Marker)
      .mock.results.find((r) => r.value.setLngLat.mock.calls[0]?.[0][1] === 33.7026)?.value;
    expect(pinMarker?.setLngLat).toHaveBeenCalledWith([-78.9001, 33.7026]);
  });

  it("does not render the map at all when the hole has no tee geometry", () => {
    render(<HoleReplayMap hole={{ ...hole, tee: null }} mapboxToken="pk.test-token" />);
    expect(mapboxgl.Map).not.toHaveBeenCalled();
  });

  it("registers a click handler that forwards the clicked lngLat to onPick", async () => {
    const onPick = vi.fn();
    render(<HoleReplayMap hole={hole} mapboxToken="pk.test-token" onPick={onPick} />);

    await waitFor(() => expect(mapboxgl.Map).toHaveBeenCalledTimes(1));
    const mapInstance = vi.mocked(mapboxgl.Map).mock.results[0].value;
    const clickHandler = mapInstance.on.mock.calls.find(
      ([event]: [string]) => event === "click"
    )?.[1];
    expect(clickHandler).toBeDefined();

    act(() => {
      clickHandler({ lngLat: { lat: 33.71, lng: -78.91 } });
    });

    expect(onPick).toHaveBeenCalledWith({ lat: 33.71, lng: -78.91 });
  });

  it("passes onPick through to the SVG fallback", () => {
    const onPick = vi.fn();
    render(<HoleReplayMap hole={hole} mapboxToken={undefined} onPick={onPick} />);
    expect(screen.getByRole("img", { name: "Hole 7 replay" })).toHaveClass("cursor-crosshair");
  });
});
