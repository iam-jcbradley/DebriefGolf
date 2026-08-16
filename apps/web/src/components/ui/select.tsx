import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

/**
 * Underline-style select — same hairline-rule treatment as `Input`, so a
 * dropdown field doesn't read as a leftover browser default next to it.
 * Pair with an <Overline> as the field label, placed above.
 */
function Select({ className, ...props }: ComponentProps<"select">) {
  return (
    <select
      data-slot="select"
      className={cn(
        "flex h-9 w-full min-w-0 border-0 border-b border-border bg-transparent px-0 py-1",
        "text-base text-foreground",
        "outline-none transition-colors",
        "focus-visible:border-primary",
        "disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50",
        "aria-invalid:border-destructive",
        "md:text-sm",
        className
      )}
      {...props}
    />
  );
}

export { Select };
