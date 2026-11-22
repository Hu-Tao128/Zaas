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

# Vite lee frontend/.env en tiempo de compilación (config de Firebase). En una
# máquina nueva hay que crear ese archivo a partir de .env.example.
RUN test -f .env || ( \
        echo "ERROR: falta frontend/.env. Copia frontend/.env.example a frontend/.env y configura Firebase." \
        && exit 1 \
    )

RUN pnpm build

# Etapa 2: servir los archivos estáticos y hacer proxy de la API hacia Flask.
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
