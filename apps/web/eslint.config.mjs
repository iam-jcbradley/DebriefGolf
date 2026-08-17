import nextConfig from "eslint-config-next";

const eslintConfig = [
  ...nextConfig,
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "out/**",
      "build/**",
      "next-env.d.ts",
    ],
  },
  {
    rules: {
      // This codebase fetches data client-side in useEffect (CLAUDE.md:
      // "Next.js is frontend-only", the browser calls FastAPI directly),
      // and the standard load/cancel/finally shape this rule targets is
      // the correct pattern for that, not an anti-pattern to eliminate.
      "react-hooks/set-state-in-effect": "warn",
    },
  },
];

export default eslintConfig;
