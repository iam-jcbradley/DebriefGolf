import { act, render, screen, waitFor } from "@testing-library/react";
import mapboxgl from "mapbox-gl";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CourseGeometryMap } from "./course-geometry-map";

vi.mock("mapbox-gl/dist/mapbox-gl.css", () => ({}));

vi.mock("mapbox-gl", () => {
  const MapMock = vi.fn(function MapMock() {
    return { on: vi.fn(), remove: vi.fn() };
  });
  const MarkerMock = vi.fn(function MarkerMock() {
    return { setLngLat: vi.fn().mockReturnThis(), addTo: vi.fn().mockReturnThis(), remove: vi.fn() };
  });
  return { default: { accessToken: "", Map: MapMock, Marker: MarkerMock } };
});

const CENTER = { lat: 33.7, lng: -78.9 };

beforeEach(() => {
  vi.mocked(mapboxgl.Map).mockClear();
  vi.mocked(mapboxgl.Marker).mockClear();
});

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function triggerLoad(mapInstance: any) {
  const loadHandler = mapInstance.on.mock.calls.find(([event]: [string]) => event === "load")?.[1];
  act(() => {
    loadHandler();
  });
}

describe("CourseGeometryMap", () => {
  it("falls back to the SVG schematic when no Mapbox token is configured", () => {
    render(
      <CourseGeometryMap
        center={CENTER}
        tee={null}
        green={null}
        boundary={[]}
        onPick={vi.fn()}
        mapboxToken={undefined}
      />
    );

    expect(screen.getByText(/needs a Mapbox token/)).toBeInTheDocument();
    expect(screen.getByRole("img")).toBeInTheDocument();
    expect(mapboxgl.Map).not.toHaveBeenCalled();
  });

  it("renders the Mapbox container instead of the SVG when a token is configured", async () => {
    render(
      <CourseGeometryMap
        center={CENTER}
        tee={null}
        green={null}
        boundary={[]}
        onPick={vi.fn()}
        mapboxToken="pk.test-token"
      />
    );

    expect(screen.getByTestId("mapbox-container")).toBeInTheDocument();
    await waitFor(() => expect(mapboxgl.Map).toHaveBeenCalledTimes(1));
  });

  it("falls back to the SVG schematic if the map reports an error", async () => {
    render(
      <CourseGeometryMap
        center={CENTER}
        tee={null}
        green={null}
        boundary={[]}
        onPick={vi.fn()}
        mapboxToken="pk.test-token"
      />
    );

    await waitFor(() => expect(mapboxgl.Map).toHaveBeenCalledTimes(1));
    const mapInstance = vi.mocked(mapboxgl.Map).mock.results[0].value;
    const errorHandler = mapInstance.on.mock.calls.find(
      ([event]: [string]) => event === "error"
    )?.[1];

    act(() => {
      errorHandler({ error: { message: "network down" } });
    });

    expect(screen.getByRole("alert")).toHaveTextContent("network down");
    expect(screen.getByRole("img")).toBeInTheDocument();
  });

  it("registers a click handler that forwards the clicked lngLat to onPick", async () => {
    const onPick = vi.fn();
    render(
      <CourseGeometryMap
        center={CENTER}
        tee={null}
        green={null}
        boundary={[]}
        onPick={onPick}
        mapboxToken="pk.test-token"
      />
    );

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

  it("adds a marker once the map loads and a tee point is set", async () => {
    render(
      <CourseGeometryMap
        center={CENTER}
        tee={CENTER}
        green={null}
        boundary={[]}
        onPick={vi.fn()}
        mapboxToken="pk.test-token"
      />
    );

    await waitFor(() => expect(mapboxgl.Map).toHaveBeenCalledTimes(1));
    const mapInstance = vi.mocked(mapboxgl.Map).mock.results[0].value;
    triggerLoad(mapInstance);

    await waitFor(() => expect(mapboxgl.Marker).toHaveBeenCalledTimes(1));
  });
});
