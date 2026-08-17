"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/settings/garmin", label: "Garmin Connect" },
  { href: "/settings/privacy", label: "Privacy & Data" },
];

/** Shared sub-navigation between the settings pages. PRD §8's nav spec is
 * a fixed 5-item list with no Settings entry, so the main `NavBar` reaches
 * these pages through the account cluster (the signed-in player's name)
 * rather than a sixth top-level link; these tabs move between them. */
export function SettingsTabs() {
  const pathname = usePathname();

  return (
    <div className="mt-6 mb-8 flex gap-4 border-b border-border">
      {TABS.map((tab) => {
        const active = pathname === tab.href;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "kicker border-b pb-2 transition-colors",
              active
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            {tab.label}
          </Link>
        );
      })}
    </div>
  );
}
