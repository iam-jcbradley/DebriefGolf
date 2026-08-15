import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Overline } from "@/components/ui/overline";
import type { Combine, WeaknessSignal } from "@/lib/api";

export interface CombineCardProps {
  combine: Combine;
  signal: WeaknessSignal;
}

/** One prescriptive practice combine (PRD §7.1) — the weakness that
 * triggered it, step-by-step instructions, the target metric to clear, and
 * a link to a curated video search. */
export function CombineCard({ combine, signal }: CombineCardProps) {
  return (
    <Card>
      <CardHeader>
        <Overline accent>Recommended combine</Overline>
        <CardTitle className="text-lg">{combine.name}</CardTitle>
        <p className="text-sm text-muted-foreground">{signal.detail}</p>
      </CardHeader>
      <CardContent>
        <p className="text-sm">{combine.instructions}</p>
        <p className="mt-3 text-sm">
          <Overline as="span">Target</Overline> <span>{combine.target_metric}</span>
        </p>
        <a
          href={combine.video_search_url}
          target="_blank"
          rel="noreferrer"
          className="mt-4 inline-block text-sm underline hover:text-primary"
        >
          Watch tutorials for this drill
        </a>
      </CardContent>
    </Card>
  );
}
