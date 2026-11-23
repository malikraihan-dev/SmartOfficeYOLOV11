FROM node:22-alpine

WORKDIR /app/frontend

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG SMARTOFFICE_API_URL=http://backend:5000
ENV SMARTOFFICE_API_URL=${SMARTOFFICE_API_URL} \
    NODE_ENV=production

RUN npm run build:compat

EXPOSE 3000

CMD ["npm", "run", "start:docker"]
