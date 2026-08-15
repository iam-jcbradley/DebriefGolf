import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

/**
 * Editorial card — a warm paper surface with a thin hairline border,
 * generous internal whitespace, and no drop shadow (per docs/STYLE_GUIDE.md:
 * "thin hairline borders instead of heavy shadows"). Composed like shadcn's
 * Card: <Card><CardHeader><CardTitle/><CardOverline/></CardHeader>
 * <CardContent/></Card>.
 */
function Card({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="card"
      className={cn(
        "rounded-md border border-border bg-card text-card-foreground",
        "flex flex-col gap-4 p-6",
        className
      )}
      {...props}
    />
  );
}

function CardHeader({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="card-header"
      className={cn("flex flex-col gap-1.5", className)}
      {...props}
    />
  );
}

function CardTitle({ className, ...props }: ComponentProps<"h3">) {
  return (
    <h3
      data-slot="card-title"
      className={cn("font-serif text-xl leading-tight font-medium", className)}
      {...props}
    />
  );
}

function CardDescription({ className, ...props }: ComponentProps<"p">) {
  return (
    <p
      data-slot="card-description"
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  );
}

function CardContent({ className, ...props }: ComponentProps<"div">) {
  return <div data-slot="card-content" className={cn(className)} {...props} />;
}

function CardFooter({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="card-footer"
      className={cn("flex items-center gap-3 border-t border-border pt-4", className)}
      {...props}
    />
  );
}

export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter };
