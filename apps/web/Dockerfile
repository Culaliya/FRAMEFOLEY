FROM node:24.4.1-bookworm-slim AS builder

WORKDIR /app
RUN corepack enable && corepack prepare pnpm@11.9.0 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
COPY packages/contracts/package.json ./packages/contracts/package.json
RUN pnpm install --frozen-lockfile

COPY apps/web ./apps/web
COPY packages/contracts ./packages/contracts
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
RUN pnpm contracts:generate && pnpm --filter @framefoley/web build

FROM node:24.4.1-bookworm-slim AS runner
ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000
WORKDIR /app
RUN addgroup --system framefoley && adduser --system --ingroup framefoley framefoley
COPY --from=builder --chown=framefoley:framefoley /app/apps/web/.next/standalone ./
COPY --from=builder --chown=framefoley:framefoley /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=framefoley:framefoley /app/apps/web/public ./apps/web/public
USER framefoley
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
