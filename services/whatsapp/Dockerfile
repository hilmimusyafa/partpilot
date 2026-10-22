FROM node:24-bookworm-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts && npm cache clean --force
COPY src ./src
RUN mkdir -p /state && chown node:node /state && chmod 700 /state
USER node
ENV NODE_ENV=production PARTPILOT_WA_STATE_DIR=/state
VOLUME ["/state"]
# Loopback only. On Linux use host networking or a shared network namespace.
CMD ["node", "src/server.js"]
