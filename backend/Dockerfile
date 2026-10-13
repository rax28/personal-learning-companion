FROM node:22-alpine
WORKDIR /app
COPY package*.json ./
COPY backend/package.json backend/package.json
RUN npm install --workspace backend
COPY backend backend
RUN npm run build --workspace backend
CMD ["node","backend/dist/src/server.js"]
