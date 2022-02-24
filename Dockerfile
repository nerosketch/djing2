FROM python:3.9

LABEL maintainer="nerosketch@gmail.com"

ENV PYTHONUNBUFFERED 1
ENV PYTHONOPTIMIZE 1
ENV APP_DEBUG y

EXPOSE ${PORT}

RUN apt-get update
RUN apt-get install -y python3-psycopg2 libsnmp-dev arping gcc gettext telnet uwsgi uwsgi-plugin-python3 --no-install-recommends
RUN mkdir -p /var/www/djing2

RUN mkdir /var/www/djing2/spooler && touch /var/www/djing2/touch_reload

COPY --chown=www-data:www-data requirements.txt /var/www/djing2
RUN pip install --no-cache-dir -r /var/www/djing2/requirements.txt
#RUN apt-get purge -y --auto-remove gcc

COPY --chown=www-data:www-data manage.py create_initial_user.py uwsgi_djing2.ini ipt_linux_agent.py pyrightconfig.json /var/www/djing2/
COPY --chown=www-data:www-data apps /var/www/djing2/apps

WORKDIR /var/www/djing2

USER www-data

CMD ./manage.py migrate \
    && ./manage.py loaddata initial_data \
    # && ./manage.py compilemessages -l ru \
    # && ./manage.py shell -c "from create_initial_user import *; make_initial_user()" \
    #&& exec uwsgi --ini /var/www/djing2/uwsgi_djing2.ini
    && exec ./manage.py runserver 0.0.0.0:${PORT}
