import type { ComponentProps, ElementType } from "react";
import { cn } from "@/lib/utils";

export interface OverlineProps extends ComponentProps<"p"> {
  /** Renders as `<span>` for inline use (e.g. inside a heading) instead of
   * the default block-level `<p>`. */
  as?: ElementType;
  /** Uses the fairway accent color instead of muted grey — for a label
   * that should read as "this is the important bit" (e.g. a section kicker
   * right above a headline), not routine secondary text. */
  accent?: boolean;
}

/**
 * Small-caps-style section label — "ROUND SUMMARY", "TODAY'S DEBRIEF".
 * Always uppercase, letter-spaced, small. See the `.overline` utility in
 * globals.css for the underlying styles and docs/STYLE_GUIDE.md for usage.
 */
function Overline({ as: Component = "p", accent = false, className, ...props }: OverlineProps) {
  return (
    <Component
      data-slot="overline"
      className={cn("overline", accent && "text-primary", className)}
      {...props}
    />
  );
}

export { Overline };
