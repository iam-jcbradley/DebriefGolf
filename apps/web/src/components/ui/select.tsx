import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

// #726A5A is --muted-foreground (globals.css). A `background-image` data
// URI can't reference a CSS custom property, so the hex is frozen here —
// keep the two in sync if the token ever moves. (A `mask-image` would track
// the token live via `background-color`, but masking the `<select>` itself
// would clip its real text content along with the decoration, so that's a
// pseudo-element-only trick and not worth a wrapper element for one arrow.)
const CHEVRON_BG =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' fill='none' stroke='%23726A5A' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E\")";

/**
 * Underline-style select — same hairline-rule treatment as `Input`, so a
 * dropdown field doesn't read as a leftover browser default next to it.
 * Pair with an <Overline> as the field label, placed above.
 *
 * `appearance-none` plus a hand-drawn chevron replaces the native dropdown
 * arrow, which at 2x device pixel ratio renders as a heavy near-black glyph
 * — the one place a native control broke STYLE_GUIDE.md §2's "never pure
 * black" rule. Focus treatment matches `Input` — see its comment.
 */
function Select({ className, ...props }: ComponentProps<"select">) {
  return (
    <select
      data-slot="select"
      className={cn(
        "flex h-9 w-full min-w-0 appearance-none border-0 border-b border-border bg-transparent bg-[length:10px_6px] bg-[right_2px_center] bg-no-repeat px-0 py-1 pr-5",
        "text-base text-foreground",
        "outline-none transition-colors",
        "focus-visible:border-b-2 focus-visible:-mb-px focus-visible:border-primary focus-visible:bg-muted/40",
        "disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50",
        "aria-invalid:border-destructive",
        "md:text-sm",
        className
      )}
      style={{ backgroundImage: CHEVRON_BG }}
      {...props}
    />
  );
}

export { Select };
