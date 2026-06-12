# ---- Stage 1: Build ----
# Install deps and build the production bundle.
# node:20-alpine is ~50 MB vs ~350 MB for the full image.

FROM node:20-alpine AS builder

WORKDIR /build

# Copy package files first → cached layer for npm install
COPY package.json package-lock.json ./
RUN npm ci --silent

# Copy source and build
COPY . .
RUN npm run build


# ---- Stage 2: Serve with nginx ----
# nginx:alpine is ~7 MB. Serves static files, reverse-proxies /api to backend.

FROM nginx:alpine

# Remove default nginx page
RUN rm -rf /usr/share/nginx/html/*

# Copy built React app
COPY --from=builder /build/dist /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
