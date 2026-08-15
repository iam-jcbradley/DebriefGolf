import Link from "next/link";

const NAV_LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/rounds", label: "Rounds" },
  { href: "/practice", label: "Practice (R10/R50)" },
  { href: "/virtual-bag", label: "Virtual Bag" },
  { href: "/share", label: "Share" },
];

export function NavBar() {
  return (
    <nav className="flex items-center gap-6 border-b px-6 py-4">
      <span className="font-semibold tracking-tight">Debrief Golf</span>
      <ul className="flex gap-4 text-sm text-muted-foreground">
        {NAV_LINKS.map((link) => (
          <li key={link.href}>
            <Link href={link.href} className="hover:text-foreground">
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
