import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement } from "react";
import { CurrentUserProvider } from "@/lib/current-user";

/** `NavBar` (rendered on every page) reads `useCurrentUser()`, which
 * requires a `CurrentUserProvider` ancestor — this wraps a page/component
 * render the same way `layout.tsx` does in the real app, so page tests
 * that don't care about *which* player is active don't have to know this
 * provider exists. Import as `render` (`import { renderWithProviders as
 * render } from "@/lib/test-utils"`) to keep every existing call site
 * unchanged. */
export function renderWithProviders(ui: ReactElement, options?: RenderOptions) {
  return render(<CurrentUserProvider>{ui}</CurrentUserProvider>, options);
}
