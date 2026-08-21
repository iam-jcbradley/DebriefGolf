import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // `next dev` (16.x) otherwise writes apps/web/AGENTS.md + apps/web/CLAUDE.md
  // on every run and neither is gitignored — the generated CLAUDE.md is just
  // `@AGENTS.md`, which would shadow this repo's real root CLAUDE.md for any
  // tooling that reads directory-local instructions if ever committed.
  agentRules: false,
};

export default nextConfig;
