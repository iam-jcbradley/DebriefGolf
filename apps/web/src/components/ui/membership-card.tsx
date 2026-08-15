import { Overline } from "@/components/ui/overline";
import { cn } from "@/lib/utils";

export interface MembershipCardProps {
  name: string;
  handicapIndex: number | null;
  club?: string | null;
  memberSince?: string | null;
  className?: string;
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "—";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

/**
 * A player's handicap/profile card, styled after a private-club membership
 * card rather than a fitness-app profile widget: a double hairline rule top
 * and bottom, a monogram instead of an avatar photo, and the handicap index
 * as the one large serif numeral — everything else is a quiet caption.
 */
function MembershipCard({ name, handicapIndex, club, memberSince, className }: MembershipCardProps) {
  return (
    <div
      className={cn(
        "relative border-t-2 border-b-2 border-double border-primary bg-card px-6 py-5",
        className
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <div
            aria-hidden="true"
            className="flex size-12 shrink-0 items-center justify-center rounded-full border border-border font-serif text-lg text-primary"
          >
            {initials(name)}
          </div>
          <div>
            <Overline>{club || "Debrief Golf"}</Overline>
            <p className="font-serif text-xl leading-tight font-medium">{name}</p>
            {memberSince && (
              <p className="mt-0.5 text-xs text-muted-foreground">Member since {memberSince}</p>
            )}
          </div>
        </div>

        <div className="text-right">
          <p className="stat-numeral text-3xl">
            {handicapIndex === null ? "—" : handicapIndex.toFixed(1)}
          </p>
          <Overline className="mt-1">Handicap</Overline>
        </div>
      </div>
    </div>
  );
}

export { MembershipCard };
