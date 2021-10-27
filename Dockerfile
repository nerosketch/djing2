FROM python:3.9

LABEL maintainer="nerosketch@gmail.com"

ENV PYTHONUNBUFFERED 1
ENV PYTHONOPTIMIZE 1
APP_DEBUG ${APP_DEBUG}

EXPOSE ${PORT}

RUN apt-get update
RUN apt-get install -y python3-psycopg2 libsnmp-dev arping gcc gettext telnet --no-install-recommends

WORKDIR /var/www/djing2
RUN mkdir ./spooler && touch ./touch_reload

COPY . .

RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get purge --auto-remove gcc

RUN chown -R www-data. ./
USER www-data

CMD ./manage.py migrate \
    && ./manage.py loaddata initial_data \
    && ./manage.py compilemessages -l ru \
    #&& ./manage.py shell -c "from create_initial_user import *; make_initial_user()" \
    && exec uwsgi --ini uwsgi_djing2.ini
