# syntax=docker/dockerfile:1.7
ARG NODE_VERSION=22

FROM node:${NODE_VERSION}-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund

COPY . .
ARG VITE_API_URL=http://localhost:18080
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build


FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
USER 101
