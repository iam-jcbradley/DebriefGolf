import { Overline } from "@/components/ui/overline";
import { cn } from "@/lib/utils";

export type StatTileTone = "good" | "bad" | "neutral";
// "delta" is for signed values where the sign itself is the story (Strokes
// Gained: up = good, down = bad) — an arrow matches the number's direction.
// "status" is for unsigned counts (Tiger 5 violation counts: 0 is good, any
// count above that is bad) — an arrow would misread as a trend, so this uses
// a status glyph instead.
export type StatTileIndicator = "delta" | "status";

export interface StatTileProps {
  label: string;
  value: string;
  tone?: StatTileTone;
  detail?: string;
  indicator?: StatTileIndicator;
}

const TONE_TEXT_CLASSES: Record<StatTileTone, string> = {
  good: "text-delta-good-text",
  bad: "text-delta-bad-text",
  neutral: "text-foreground",
};

function glyphFor(tone: StatTileTone, indicator: StatTileIndicator): string | null {
  if (tone === "neutral") return null;
  if (indicator === "delta") return tone === "good" ? "↑" : "↓";
  return tone === "good" ? "✓" : "⚠";
}

/**
 * The project's stat-display component — a large serif numeral with a
 * small overline caption beneath, per docs/STYLE_GUIDE.md's "numeric/stat
 * display" treatment. Named StatTile (not StatDisplay) for historical
 * reasons: it predates the design system and is already threaded through
 * RoundSnapshot/TigerFiveMeter/Smart Bag — the style guide notes this
 * mapping explicitly.
 */
export function StatTile({
  label,
  value,
  tone = "neutral",
  detail,
  indicator = "delta",
}: StatTileProps) {
  const glyph = glyphFor(tone, indicator);

  return (
    <div className="border border-border bg-card px-4 py-3">
      <p className={cn("stat-numeral text-3xl", TONE_TEXT_CLASSES[tone])}>
        {glyph && <span aria-hidden="true">{glyph} </span>}
        {value}
      </p>
      <Overline className="mt-1.5">{label}</Overline>
      {detail && <p className="mt-0.5 text-xs text-muted-foreground">{detail}</p>}
    </div>
  );
}
