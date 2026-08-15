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

export function StatTile({ label, value, tone = "neutral", detail, indicator = "delta" }: StatTileProps) {
  const glyph = glyphFor(tone, indicator);

  return (
    <div className="rounded-lg border bg-card p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className={cn("text-2xl font-semibold", TONE_TEXT_CLASSES[tone])}>
        {glyph && <span aria-hidden="true">{glyph} </span>}
        {value}
      </p>
      {detail && <p className="text-xs text-muted-foreground">{detail}</p>}
    </div>
  );
}
