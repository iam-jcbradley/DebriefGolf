/**
 * Names the marks on the hole canvas. Without it a reader has to guess
 * what the black dot, the green dot and the flag mean — the canvas is the
 * one place in the app that communicates purely in symbols.
 *
 * Swatches are typographic/geometric, not an icon set (STYLE_GUIDE.md §4).
 */
const ITEMS: Array<{ color: string; label: string }> = [
  { color: "var(--foreground)", label: "Tee" },
  { color: "var(--primary)", label: "Shot" },
  { color: "var(--status-critical)", label: "Short-sided" },
  { color: "var(--status-good)", label: "Green" },
];

export interface HoleReplayLegendProps {
  hasPin: boolean;
  /** True when the canvas fitted its lateral axis to the shots rather than
   * sharing the along-hole scale. Say so: at a typical fit the sideways
   * spread is magnified several times over, and a reader who assumes one
   * scale would take a 5-yard miss for a 30-yard one. */
  lateralExaggerated?: boolean;
}

export function HoleReplayLegend({ hasPin, lateralExaggerated = false }: HoleReplayLegendProps) {
  return (
    <>
      <ul className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {ITEMS.map(({ color, label }) => (
          <li key={label} className="flex items-center gap-1.5">
            <span
              aria-hidden="true"
              className="inline-block size-2 rounded-full"
              style={{ backgroundColor: color }}
            />
            {label}
          </li>
        ))}
        {hasPin && (
          <li className="flex items-center gap-1.5">
            <span aria-hidden="true" className="text-primary">
              ⚑
            </span>
            Pin
          </li>
        )}
      </ul>
      {lateralExaggerated && (
        <p className="mt-2 text-xs text-muted-foreground">
          Distance along the hole is to scale; side-to-side spread is magnified so the
          shot shapes are readable.
        </p>
      )}
    </>
  );
}
