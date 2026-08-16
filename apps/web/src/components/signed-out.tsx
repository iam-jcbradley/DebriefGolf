"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Overline } from "@/components/ui/overline";

export interface SignedOutProps {
  description: string;
}

/** The empty state every player-scoped page falls back to when nobody is
 * signed in. Replaces `NoPlayerSelected`, whose "choose a player" button
 * opened a picker listing everyone's names — an identity you could simply
 * select is what Phase 10 removed. */
export function SignedOut({ description }: SignedOutProps) {
  return (
    <Card>
      <CardHeader>
        <Overline>Not signed in</Overline>
        <CardTitle className="text-lg">Sign in to continue</CardTitle>
        <p className="text-sm text-muted-foreground">{description}</p>
      </CardHeader>
      <CardContent>
        <Link
          href="/login"
          className="inline-flex h-10 items-center rounded-sm bg-primary px-5 text-sm text-primary-foreground transition-colors hover:bg-accent-hover"
        >
          Sign in
        </Link>
      </CardContent>
    </Card>
  );
}
