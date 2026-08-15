"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/settings/garmin", label: "Garmin Connect" },
  { href: "/settings/privacy", label: "Privacy & Data" },
];

/** Shared sub-navigation between the settings pages — neither is linked
 * from the main `NavBar` (PRD §8's nav spec is a fixed 5-item list with no
 * Settings entry), so this is what ties them together for a user who
 * already knows one of the URLs. */
export function SettingsTabs() {
  const pathname = usePathname();

  return (
    <div className="mb-8 flex gap-4 border-b border-border">
      {TABS.map((tab) => {
        const active = pathname === tab.href;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "overline border-b pb-2 transition-colors",
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
