FROM python:3

LABEL maintainer="nerosketch@gmail.com"

ENV PYTHONUNBUFFERED 1
ENV APP_DEBUG y

EXPOSE 8000

RUN apt-get update
RUN apt-get install -y git python3-psycopg2 libsnmp-dev arping gcc gettext --no-install-recommends
RUN mkdir ./spooler && touch ./touch_reload && mkdir -p /usr/src/app/conf/apps/djing2

RUN git clone --depth=1 git://github.com/nerosketch/djing2.git -b devel /var/www/djing2

RUN pip install --no-cache-dir -r /var/www/djing2/requirements.txt

COPY create_initial_user.py /usr/src/app/conf
COPY local_settings.py /usr/src/app/conf/apps/djing2

WORKDIR /var/www/djing2

CMD cp -Rv /usr/src/app/conf/* ./ \
    && ./manage.py migrate \
    && ./manage.py loaddata initial_data \
    #&& ./manage.py compilemessages -l ru \
    && ./manage.py shell -c "from create_initial_user import *; make_initial_user()" \
    && exec ./manage.py runserver 0.0.0.0:8000
