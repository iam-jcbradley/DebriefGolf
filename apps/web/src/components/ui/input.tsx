import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

/**
 * Underline-style input — a single hairline rule rather than a boxed field,
 * matching a membership-form / ledger feel (docs/STYLE_GUIDE.md). Pair with
 * an <Overline> as the field label, placed above.
 *
 * Focus thickens the rule to 2px (`-mb-px` cancels the extra height so nothing
 * shifts) and tints the field, per STYLE_GUIDE.md §4's Focus rule — a 1px
 * color change alone falls under WCAG 2.4.13's indicator-size floor, and
 * next to a .kicker label in the same muted-on-paper palette it was easy to
 * miss which field actually had focus.
 */
function Input({ className, type, ...props }: ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "flex h-9 w-full min-w-0 border-0 border-b border-border bg-transparent px-0 py-1",
        "text-base text-foreground placeholder:text-muted-foreground",
        "outline-none transition-colors selection:bg-primary selection:text-primary-foreground",
        "focus-visible:border-b-2 focus-visible:-mb-px focus-visible:border-primary focus-visible:bg-muted/40",
        "disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50",
        "aria-invalid:border-destructive",
        "md:text-sm",
        className
      )}
      {...props}
    />
  );
}

export { Input };
