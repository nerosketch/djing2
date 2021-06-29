FROM alpine

EXPOSE 3211

ARG APP_DIR=/app

ENV PATH $PATH:${APP_DIR}

RUN mkdir ${APP_DIR}

WORKDIR ${APP_DIR}

COPY djing_ws ${APP_DIR}

CMD [ "djing_ws", "-addr", "0.0.0.0:3211" ]
