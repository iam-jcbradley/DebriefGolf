import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, createUser, searchUsers } from "@/lib/api";
import { PlayerSwitcherDialog } from "./player-switcher-dialog";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, searchUsers: vi.fn(), createUser: vi.fn() };
});

const mockSearchUsers = vi.mocked(searchUsers);
const mockCreateUser = vi.mocked(createUser);

beforeEach(() => {
  mockSearchUsers.mockReset();
  mockCreateUser.mockReset();
  mockSearchUsers.mockResolvedValue([]);
});

describe("PlayerSwitcherDialog", () => {
  it("renders nothing when closed", () => {
    render(
      <PlayerSwitcherDialog
        open={false}
        currentUser={null}
        onClose={vi.fn()}
        onSelect={vi.fn()}
        onClear={vi.fn()}
      />
    );
    expect(screen.queryByText("Who's playing?")).not.toBeInTheDocument();
  });

  it("shows the search prompt when open", () => {
    render(
      <PlayerSwitcherDialog
        open
        currentUser={null}
        onClose={vi.fn()}
        onSelect={vi.fn()}
        onClear={vi.fn()}
      />
    );
    expect(screen.getByText("Who's playing?")).toBeInTheDocument();
    expect(screen.getByLabelText("Name")).toBeInTheDocument();
  });

  it("searches as the user types and lists matches", async () => {
    mockSearchUsers.mockResolvedValue([{ id: 5, name: "Jane Doe" }]);
    const user = userEvent.setup();

    render(
      <PlayerSwitcherDialog
        open
        currentUser={null}
        onClose={vi.fn()}
        onSelect={vi.fn()}
        onClear={vi.fn()}
      />
    );
    await user.type(screen.getByLabelText("Name"), "Jane");

    expect(await screen.findByRole("button", { name: "Jane Doe" })).toBeInTheDocument();
    expect(mockSearchUsers).toHaveBeenCalledWith("Jane");
  });

  it("selects an existing player from the search results", async () => {
    mockSearchUsers.mockResolvedValue([{ id: 5, name: "Jane Doe" }]);
    const onSelect = vi.fn();
    const user = userEvent.setup();

    render(
      <PlayerSwitcherDialog
        open
        currentUser={null}
        onClose={vi.fn()}
        onSelect={onSelect}
        onClear={vi.fn()}
      />
    );
    await user.type(screen.getByLabelText("Name"), "Jane");
    await user.click(await screen.findByRole("button", { name: "Jane Doe" }));

    expect(onSelect).toHaveBeenCalledWith({ id: 5, name: "Jane Doe" });
  });

  it("offers to create a new player once enough of a name is typed", async () => {
    const user = userEvent.setup();
    render(
      <PlayerSwitcherDialog
        open
        currentUser={null}
        onClose={vi.fn()}
        onSelect={vi.fn()}
        onClear={vi.fn()}
      />
    );
    await user.type(screen.getByLabelText("Name"), "New Person");

    expect(
      await screen.findByRole("button", { name: /create "new person" as a new player/i })
    ).toBeInTheDocument();
  });

  it("creates a player with the typed name and entered email", async () => {
    mockCreateUser.mockResolvedValue({
      id: 9, email: "new@example.com", name: "New Person", handicap_index: 0,
      created_at: "2026-01-01T00:00:00Z",
    });
    const onSelect = vi.fn();
    const user = userEvent.setup();

    render(
      <PlayerSwitcherDialog
        open
        currentUser={null}
        onClose={vi.fn()}
        onSelect={onSelect}
        onClear={vi.fn()}
      />
    );
    await user.type(screen.getByLabelText("Name"), "New Person");
    await user.click(
      await screen.findByRole("button", { name: /create "new person" as a new player/i })
    );
    await user.type(screen.getByLabelText("Email"), "new@example.com");
    await user.click(screen.getByRole("button", { name: "Create player" }));

    expect(mockCreateUser).toHaveBeenCalledWith({ name: "New Person", email: "new@example.com" });
    expect(onSelect).toHaveBeenCalledWith({ id: 9, name: "New Person" });
  });

  it("shows an error when creating a player fails", async () => {
    mockCreateUser.mockRejectedValue(new ApiError(409, "A player with this email already exists"));
    const user = userEvent.setup();

    render(
      <PlayerSwitcherDialog
        open
        currentUser={null}
        onClose={vi.fn()}
        onSelect={vi.fn()}
        onClear={vi.fn()}
      />
    );
    await user.type(screen.getByLabelText("Name"), "New Person");
    await user.click(
      await screen.findByRole("button", { name: /create "new person" as a new player/i })
    );
    await user.type(screen.getByLabelText("Email"), "dup@example.com");
    await user.click(screen.getByRole("button", { name: "Create player" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "A player with this email already exists"
    );
  });

  it("shows a clear-player link only when a current player is set", () => {
    const { rerender } = render(
      <PlayerSwitcherDialog
        open
        currentUser={null}
        onClose={vi.fn()}
        onSelect={vi.fn()}
        onClear={vi.fn()}
      />
    );
    expect(screen.queryByText(/clear saved player/i)).not.toBeInTheDocument();

    rerender(
      <PlayerSwitcherDialog
        open
        currentUser={{ id: 1, name: "Jane Doe" }}
        onClose={vi.fn()}
        onSelect={vi.fn()}
        onClear={vi.fn()}
      />
    );
    expect(screen.getByText(/clear saved player/i)).toBeInTheDocument();
  });

  it("calls onClear when the clear-player link is clicked", async () => {
    const onClear = vi.fn();
    const user = userEvent.setup();

    render(
      <PlayerSwitcherDialog
        open
        currentUser={{ id: 1, name: "Jane Doe" }}
        onClose={vi.fn()}
        onSelect={vi.fn()}
        onClear={onClear}
      />
    );
    await user.click(screen.getByText(/clear saved player/i));

    expect(onClear).toHaveBeenCalled();
  });
});
