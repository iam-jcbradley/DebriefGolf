import { cn } from "@/lib/utils";

export interface DividerProps {
  /** The centered glyph — a small star for a formal section break, a dot
   * for a quieter one between closely related pieces of content. */
  glyph?: "star" | "dot";
  className?: string;
}

const GLYPHS: Record<NonNullable<DividerProps["glyph"]>, string> = {
  star: "✦",
  dot: "•",
};

/**
 * A thin rule broken by a small centered glyph — the section break used
 * throughout the editorial layout instead of heavy card stacking or bold
 * headings. Purely decorative, so the glyph is hidden from assistive tech;
 * the divider itself is exposed as a semantic separator.
 */
function Divider({ glyph = "star", className }: DividerProps) {
  return (
    <div
      role="separator"
      aria-orientation="horizontal"
      className={cn("my-6 flex items-center gap-3", className)}
    >
      <div className="h-px flex-1 bg-border" />
      <span aria-hidden="true" className="text-xs text-muted-foreground">
        {GLYPHS[glyph]}
      </span>
      <div className="h-px flex-1 bg-border" />
    </div>
  );
}

export { Divider };
