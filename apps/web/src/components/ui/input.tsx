import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

/**
 * Underline-style input — a single hairline rule rather than a boxed field,
 * matching a membership-form / ledger feel (docs/STYLE_GUIDE.md). Pair with
 * an <Overline> as the field label, placed above.
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

export { Input };
