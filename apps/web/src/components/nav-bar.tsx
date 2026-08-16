"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { useCurrentUser } from "@/lib/current-user";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/rounds", label: "Rounds" },
  { href: "/practice", label: "Practice" },
  { href: "/virtual-bag", label: "Virtual Bag" },
];

function isActive(pathname: string | null, href: string): boolean {
  if (!pathname) return false;
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

const navLinkClass = (active: boolean) =>
  cn(
    "overline border-b pb-0.5 transition-colors",
    active ? "border-primary text-foreground" : "border-transparent hover:text-foreground"
  );

const mutedLinkClass =
  "overline border-b border-transparent pb-0.5 text-muted-foreground transition-colors hover:border-primary hover:text-foreground";

/**
 * A masthead, not a toolbar — serif wordmark, uppercase text links, an
 * understated underline for the active page. No pills, no tabs, no icons.
 *
 * Below `md`, the link row and the account cluster collapse behind a text
 * "Menu" toggle instead of a hamburger glyph — icons are off-limits per the
 * style guide, and at phone widths the full row otherwise collides with the
 * wordmark and pushes "Sign out" off the right edge of the viewport.
 */
export function NavBar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading, signOut } = useCurrentUser();
  const [menuOpen, setMenuOpen] = useState(false);

  async function handleSignOut() {
    setMenuOpen(false);
    await signOut();
    router.push("/login");
  }

  return (
    <nav className="border-b border-border">
      <div className="flex items-center justify-between px-6 py-5">
        <Link href="/" className="font-serif text-lg tracking-tight" onClick={() => setMenuOpen(false)}>
          Debrief Golf
        </Link>

        <div className="hidden items-center gap-6 md:flex">
          <ul className="flex gap-6">
            {NAV_LINKS.map((link) => (
              <li key={link.href}>
                <Link href={link.href} aria-current={isActive(pathname, link.href) ? "page" : undefined} className={navLinkClass(isActive(pathname, link.href))}>
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
          {loading ? null : user ? (
            <div className="flex items-center gap-4">
              <Link href="/settings/garmin" className={mutedLinkClass}>
                {user.name}
              </Link>
              <button type="button" onClick={handleSignOut} className={mutedLinkClass}>
                Sign out
              </button>
            </div>
          ) : (
            <Link href="/login" className={mutedLinkClass}>
              Sign in
            </Link>
          )}
        </div>

        <button
          type="button"
          className="overline border-b border-transparent pb-0.5 text-foreground md:hidden"
          aria-expanded={menuOpen}
          aria-controls="mobile-nav-panel"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? "Close" : "Menu"}
        </button>
      </div>

      {menuOpen && (
        <div id="mobile-nav-panel" className="border-t border-border px-6 py-4 md:hidden">
          <ul className="flex flex-col gap-4">
            {NAV_LINKS.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  aria-current={isActive(pathname, link.href) ? "page" : undefined}
                  className={navLinkClass(isActive(pathname, link.href))}
                  onClick={() => setMenuOpen(false)}
                >
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
          <div className="mt-5 flex flex-col gap-4 border-t border-border pt-4">
            {loading ? null : user ? (
              <>
                <Link href="/settings/garmin" className={mutedLinkClass} onClick={() => setMenuOpen(false)}>
                  {user.name} &middot; Settings
                </Link>
                <button type="button" onClick={handleSignOut} className={cn(mutedLinkClass, "text-left")}>
                  Sign out
                </button>
              </>
            ) : (
              <Link href="/login" className={mutedLinkClass} onClick={() => setMenuOpen(false)}>
                Sign in
              </Link>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
