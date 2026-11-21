FROM node:20-alpine

ENV NEXT_TELEMETRY_DISABLED=1 \
    TZ=Europe/Istanbul

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
