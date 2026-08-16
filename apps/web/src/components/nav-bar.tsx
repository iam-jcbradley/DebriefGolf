"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCurrentUser } from "@/lib/current-user";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/rounds", label: "Rounds" },
  { href: "/practice", label: "Practice" },
  { href: "/virtual-bag", label: "Virtual Bag" },
  { href: "/share", label: "Share" },
];

function isActive(pathname: string | null, href: string): boolean {
  if (!pathname) return false;
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

/**
 * A masthead, not a toolbar — serif wordmark, uppercase text links, an
 * understated underline for the active page. No pills, no tabs, no icons.
 */
export function NavBar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading, signOut } = useCurrentUser();

  return (
    <nav className="flex items-center justify-between border-b border-border px-6 py-5">
      <Link href="/" className="font-serif text-lg tracking-tight">
        Debrief Golf
      </Link>
      <div className="flex items-center gap-6">
        <ul className="flex gap-6">
          {NAV_LINKS.map((link) => {
            const active = isActive(pathname, link.href);
            return (
              <li key={link.href}>
                <Link
                  href={link.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "overline border-b pb-0.5 transition-colors",
                    active
                      ? "border-primary text-foreground"
                      : "border-transparent hover:text-foreground"
                  )}
                >
                  {link.label}
                </Link>
              </li>
            );
          })}
        </ul>
        {loading ? null : user ? (
          <div className="flex items-center gap-4">
            <span className="overline text-muted-foreground">{user.name}</span>
            <button
              type="button"
              onClick={async () => {
                await signOut();
                router.push("/login");
              }}
              className="overline border-b border-transparent pb-0.5 text-muted-foreground transition-colors hover:border-primary hover:text-foreground"
            >
              Sign out
            </button>
          </div>
        ) : (
          <Link
            href="/login"
            className="overline border-b border-transparent pb-0.5 text-muted-foreground transition-colors hover:border-primary hover:text-foreground"
          >
            Sign in
          </Link>
        )}
      </div>
    </nav>
  );
}
