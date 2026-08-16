import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createCourse,
  getOsmCourseGeometry,
  searchOsmCourses,
  type CourseDetail,
  type OsmCourseDraft,
  type OsmCourseSummary,
} from "@/lib/api";
import { renderWithProviders as render } from "@/lib/test-utils";
import NewCoursePage from "./page";

vi.mock("mapbox-gl/dist/mapbox-gl.css", () => ({}));
vi.mock("mapbox-gl", () => ({
  default: { accessToken: "", Map: vi.fn(), Marker: vi.fn() },
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    searchOsmCourses: vi.fn(),
    getOsmCourseGeometry: vi.fn(),
    createCourse: vi.fn(),
  };
});

const mockSearchOsmCourses = vi.mocked(searchOsmCourses);
const mockGetOsmCourseGeometry = vi.mocked(getOsmCourseGeometry);
const mockCreateCourse = vi.mocked(createCourse);

beforeEach(() => {
  mockSearchOsmCourses.mockReset();
  mockGetOsmCourseGeometry.mockReset();
  mockCreateCourse.mockReset();
});

async function goToBuildStepFromScratch(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: /start from scratch/i }));
}

describe("NewCoursePage", () => {
  it("renders the search form initially", () => {
    render(<NewCoursePage />);
    expect(screen.getByPlaceholderText(/search openstreetmap/i)).toBeInTheDocument();
  });

  it("searches OSM and lists results", async () => {
    const results: OsmCourseSummary[] = [
      {
        osm_type: "way", osm_id: 123, name: "Pinehurst Creek Golf Club",
        city: "Pawleys Island", state: "SC", center: { lat: 33.7, lng: -78.9 },
      },
    ];
    mockSearchOsmCourses.mockResolvedValue(results);
    const user = userEvent.setup();

    render(<NewCoursePage />);
    await user.type(screen.getByPlaceholderText(/search openstreetmap/i), "Pinehurst");
    await user.click(screen.getByRole("button", { name: "Search" }));

    expect(await screen.findByText("Pinehurst Creek Golf Club")).toBeInTheDocument();
    expect(mockSearchOsmCourses).toHaveBeenCalledWith("Pinehurst");
  });

  it("shows a message when search returns no results", async () => {
    mockSearchOsmCourses.mockResolvedValue([]);
    const user = userEvent.setup();

    render(<NewCoursePage />);
    await user.type(screen.getByPlaceholderText(/search openstreetmap/i), "Nowhere GC");
    await user.click(screen.getByRole("button", { name: "Search" }));

    expect(await screen.findByText(/no matches on openstreetmap/i)).toBeInTheDocument();
  });

  it("shows a search error", async () => {
    mockSearchOsmCourses.mockRejectedValue(new Error("blocked"));
    const user = userEvent.setup();

    render(<NewCoursePage />);
    await user.type(screen.getByPlaceholderText(/search openstreetmap/i), "Pinehurst");
    await user.click(screen.getByRole("button", { name: "Search" }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });

  it("prefills course fields and holes from a chosen OSM result", async () => {
    const results: OsmCourseSummary[] = [
      {
        osm_type: "way", osm_id: 123, name: "Pinehurst Creek Golf Club",
        city: "Pawleys Island", state: "SC", center: { lat: 33.7, lng: -78.9 },
      },
    ];
    const draft: OsmCourseDraft = {
      name: "Pinehurst Creek Golf Club", city: "Pawleys Island", state: "SC", osm_relation_id: 123,
      holes: [
        {
          number: 1, par: 4, yardage: 400,
          tee_location: { lat: 33.7, lng: -78.9 }, green_center: { lat: 33.7025, lng: -78.9 },
          green_boundary: null,
        },
        { number: 2, par: null, yardage: null, tee_location: null, green_center: null, green_boundary: null },
      ],
    };
    mockSearchOsmCourses.mockResolvedValue(results);
    mockGetOsmCourseGeometry.mockResolvedValue(draft);
    const user = userEvent.setup();

    render(<NewCoursePage />);
    await user.type(screen.getByPlaceholderText(/search openstreetmap/i), "Pinehurst");
    await user.click(screen.getByRole("button", { name: "Search" }));
    await user.click(await screen.findByRole("button", { name: /use this course/i }));

    expect(await screen.findByDisplayValue("Pinehurst Creek Golf Club")).toBeInTheDocument();
    expect(mockGetOsmCourseGeometry).toHaveBeenCalledWith("way", 123);
    // hole 1 came in complete (yardage prefilled); hole 2 needs par/yardage
    expect(screen.getByRole("button", { name: "Save course" })).toBeDisabled();
  });

  it("starts a blank course and lets the user add holes", async () => {
    const user = userEvent.setup();
    render(<NewCoursePage />);

    await goToBuildStepFromScratch(user);
    expect(screen.getByLabelText("Course name")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save course" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Add hole" }));
    expect(screen.getByText("Hole")).toBeInTheDocument();
  });

  it("removes a hole", async () => {
    const user = userEvent.setup();
    render(<NewCoursePage />);
    await goToBuildStepFromScratch(user);

    await user.click(screen.getByRole("button", { name: "Add hole" }));
    expect(screen.getByRole("button", { name: "Remove" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Remove" }));
    expect(screen.queryByRole("button", { name: "Remove" })).not.toBeInTheDocument();
  });

  it("enables Save once name and a complete hole are provided, then saves", async () => {
    const created: CourseDetail = {
      id: 42, name: "My New Course", city: null, state: null, osm_relation_id: null,
      holes: [{ hole_number: 1, par: 4, yardage: 400, tee: null, green_center: null, green_boundary: null }],
    };
    mockCreateCourse.mockResolvedValue(created);
    const user = userEvent.setup();

    render(<NewCoursePage />);
    await goToBuildStepFromScratch(user);
    await user.type(screen.getByLabelText("Course name"), "My New Course");
    await user.click(screen.getByRole("button", { name: "Add hole" }));

    await user.type(screen.getByLabelText("Yardage"), "400");

    const saveButton = screen.getByRole("button", { name: "Save course" });
    expect(saveButton).toBeEnabled();
    await user.click(saveButton);

    expect(await screen.findByText(/course saved/i)).toBeInTheDocument();
    expect(mockCreateCourse).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "My New Course",
        holes: [expect.objectContaining({ number: 1, par: 4, yardage: 400 })],
      })
    );
    expect(screen.getByRole("link", { name: /create a round/i })).toHaveAttribute(
      "href",
      "/rounds/new?course_id=42"
    );
  });

  it("shows a validation message for duplicate hole numbers", async () => {
    const user = userEvent.setup();
    render(<NewCoursePage />);
    await goToBuildStepFromScratch(user);

    await user.click(screen.getByRole("button", { name: "Add hole" }));
    await user.click(screen.getByRole("button", { name: "Add hole" }));

    const numberInputs = screen.getAllByLabelText("Hole");
    fireEvent.change(numberInputs[1], { target: { value: "1" } });

    expect(screen.getByText(/hole numbers must be unique/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save course" })).toBeDisabled();
  });

  it("shows a save error and stays on the build step", async () => {
    mockCreateCourse.mockRejectedValue(new Error("failed"));
    const user = userEvent.setup();

    render(<NewCoursePage />);
    await goToBuildStepFromScratch(user);
    await user.type(screen.getByLabelText("Course name"), "My New Course");
    await user.click(screen.getByRole("button", { name: "Add hole" }));
    await user.type(screen.getByLabelText("Yardage"), "400");

    await user.click(screen.getByRole("button", { name: "Save course" }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.queryByText(/course saved/i)).not.toBeInTheDocument();
  });
});
