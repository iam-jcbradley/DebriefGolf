"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Overline } from "@/components/ui/overline";
import { useCurrentUser } from "@/lib/current-user";

export interface NoPlayerSelectedProps {
  description: string;
}

/** The empty state every player-scoped page falls back to when
 * `useCurrentUser()` has no player yet — replaces what used to be each
 * page's own numeric "User ID" input. */
export function NoPlayerSelected({ description }: NoPlayerSelectedProps) {
  const { openPicker } = useCurrentUser();

  return (
    <Card>
      <CardHeader>
        <Overline>No player chosen</Overline>
        <CardTitle className="text-lg">Choose a player to continue</CardTitle>
        <p className="text-sm text-muted-foreground">{description}</p>
      </CardHeader>
      <CardContent>
        <Button type="button" onClick={openPicker}>
          Choose player
        </Button>
      </CardContent>
    </Card>
  );
}
