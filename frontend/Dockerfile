# Etapa 1: compilar la SPA de React con Vite.
FROM node:20-alpine AS build

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@9.15.9 --activate

# Se copian primero los manifiestos para aprovechar la caché de capas.
# No se copia pnpm-workspace.yaml: define opciones de pnpm 12 y aquí se usa
# pnpm 9 como proyecto único.
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .

# Vite incrusta las variables VITE_* en tiempo de build. Se aceptan como build
# args para que Coolify (Build Variables) u otro CI pueda inyectarlas sin
# necesidad de un archivo .env. Si existe frontend/.env también se respeta.
ARG VITE_FIREBASE_API_KEY
ARG VITE_FIREBASE_AUTH_DOMAIN
ARG VITE_FIREBASE_PROJECT_ID
ARG VITE_FIREBASE_STORAGE_BUCKET
ARG VITE_FIREBASE_MESSAGING_SENDER_ID
ARG VITE_FIREBASE_APP_ID
ARG VITE_FIREBASE_MEASUREMENT_ID

ENV VITE_FIREBASE_API_KEY=${VITE_FIREBASE_API_KEY} \
    VITE_FIREBASE_AUTH_DOMAIN=${VITE_FIREBASE_AUTH_DOMAIN} \
    VITE_FIREBASE_PROJECT_ID=${VITE_FIREBASE_PROJECT_ID} \
    VITE_FIREBASE_STORAGE_BUCKET=${VITE_FIREBASE_STORAGE_BUCKET} \
    VITE_FIREBASE_MESSAGING_SENDER_ID=${VITE_FIREBASE_MESSAGING_SENDER_ID} \
    VITE_FIREBASE_APP_ID=${VITE_FIREBASE_APP_ID} \
    VITE_FIREBASE_MEASUREMENT_ID=${VITE_FIREBASE_MEASUREMENT_ID}

RUN pnpm build

# Etapa 2: servir los archivos estáticos y hacer proxy de la API hacia Flask.
FROM nginx:1.27-alpine

# El entrypoint de nginx sustituye ${BACKEND_URL} dentro de la plantilla.
# En docker-compose el backend se resuelve como "backend"; en despliegues
# separados (Coolify) apunta a la URL del servicio de backend.
ENV BACKEND_URL=http://backend:5000

COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=5 \
    CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
