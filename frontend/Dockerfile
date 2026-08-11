FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json .

RUN npm config set fetch-timeout 120000
RUN npm config set fetch-retries 5

# Note: `npm install` requires network access at build time (it is not run
# offline). The app uses relative /api and /ws URLs, so no VITE_* build-time
# env vars are needed.
RUN npm install

COPY . .

RUN npm run build


FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

COPY nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx","-g","daemon off;"]
