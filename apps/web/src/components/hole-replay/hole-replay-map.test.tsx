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
  green_boundary: null,
  shots: [],
  short_sided_count: 0,
};

beforeEach(() => {
  vi.mocked(mapboxgl.Map).mockClear();
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

  it("does not render the map at all when the hole has no tee geometry", () => {
    render(<HoleReplayMap hole={{ ...hole, tee: null }} mapboxToken="pk.test-token" />);
    expect(mapboxgl.Map).not.toHaveBeenCalled();
  });
});
