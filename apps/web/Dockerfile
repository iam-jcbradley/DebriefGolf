FROM node:26-slim AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
# Node 26 no longer ships corepack by default (removed from core in
# Node 25+); install it explicitly before enabling it.
RUN npm install -g corepack@latest && corepack enable
WORKDIR /app
COPY package.json ./
RUN corepack install

FROM base AS deps
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile

FROM base AS dev
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
CMD ["pnpm", "dev"]

FROM base AS build
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN pnpm build

FROM base AS prod
ENV NODE_ENV=production
# No public/ directory to copy — this app uses the App Router's own
# src/app/favicon.ico convention, not a public/ folder, so there's nothing
# here for a `public/` COPY to pick up (and one always failed the build
# outright when this line assumed otherwise).
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
