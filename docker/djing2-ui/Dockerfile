FROM node:10

EXPOSE 8080

ENV VUE_APP_BASE_API=http://localhost:8000/api
ENV NODE_ENV=development

ARG APP_DIR=/home/node/app
ARG NODE_ENV=development

RUN apt-get -y update && apt-get -y install --no-install-recommends git

USER node

RUN git clone --depth=1 git://github.com/nerosketch/djing2-elui.git ${APP_DIR}

WORKDIR ${APP_DIR}

RUN npm install

COPY . .

CMD [ "npm", "run", "--silent", "serve" ]
