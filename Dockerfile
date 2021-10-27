FROM python:3.9

LABEL maintainer="nerosketch@gmail.com"

ENV PYTHONUNBUFFERED 1
ENV PYTHONOPTIMIZE 1
ENV APP_DEBUG ${APP_DEBUG}

# ENV SECRETS_DIR_PATH ${SECRETS_DIR_PATH}
ENV ALLOWED_HOSTS ${ALLOWED_HOSTS}
ENV DEFAULT_EMAIL ${DEFAULT_EMAIL}
ENV ADMINS ${ADMINS}
ENV POSTGRES_DB ${POSTGRES_DB}
ENV POSTGRES_USER ${POSTGRES_USER}
ENV POSTGRES_HOST ${POSTGRES_HOST}
ENV API_AUTH_SUBNET ${API_AUTH_SUBNET}
ENV MESSENGER_BOT_PUBLIC_URL ${MESSENGER_BOT_PUBLIC_URL}
ENV ARPING_COMMAND ${ARPING_COMMAND}
ENV ARPING_ENABLED ${ARPING_ENABLED}
ENV SORM_EXPORT_FTP_HOST ${SORM_EXPORT_FTP_HOST}
ENV SORM_EXPORT_FTP_USERNAME ${SORM_EXPORT_FTP_USERNAME}
ENV RADIUS_APP_HOST ${RADIUS_APP_HOST}

EXPOSE ${PORT}

RUN apt-get update
RUN apt-get install -y python3-psycopg2 libsnmp-dev arping gcc gettext telnet --no-install-recommends

WORKDIR /var/www/djing2
RUN mkdir ./spooler && touch ./touch_reload

COPY . .

RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get purge -y --auto-remove gcc

RUN chown -R www-data. ./
USER www-data

CMD ./manage.py migrate \
    && ./manage.py loaddata initial_data \
    && ./manage.py compilemessages -l ru \
    #&& ./manage.py shell -c "from create_initial_user import *; make_initial_user()" \
    && exec uwsgi --ini uwsgi_djing2.ini
