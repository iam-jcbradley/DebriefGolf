import { NavBar } from "@/components/nav-bar";

export default function DashboardPage() {
  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="flex flex-col items-center justify-center gap-4 px-6 py-24 text-center">
        <h1 className="text-3xl font-semibold tracking-tight">
          Debrief Golf
        </h1>
        <p className="max-w-md text-muted-foreground">
          Arccos-grade Strokes Gained diagnostics, dispersion modeling, and
          prescriptive learning for the Garmin Golf ecosystem. This is a
          bootstrap placeholder — the round snapshot, Tiger 5 disaster meter,
          and hole replay engine land in later development phases.
        </p>
      </main>
    </div>
  );
}
