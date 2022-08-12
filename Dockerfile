FROM python:3.9-alpine

LABEL maintainer="nerosketch@gmail.com"

ENV PYTHONUNBUFFERED=1
ENV PYTHONOPTIMIZE=1
ENV DJING2_LOG_FILE=/var/log/djing2/main.log
ENV PYTHONIOENCODING=UTF-8

RUN ["apk", "add", "py3-psycopg2", "net-snmp-dev", "arping", "gettext", "inetutils-telnet", "gcc", "git", "musl-dev", "libffi-dev", "libpq-dev", "make", "--no-cache"]
RUN ["adduser", "-G", "www-data", "-SDH", "-h", "/var/www/djing2", "www-data"]
RUN mkdir -p /var/www/djing2/media /var/log/djing2 \
    && touch /var/www/djing2/touch_reload \
    && chown -R www-data. /var/www/djing2 /var/log/djing2

COPY --chown=www-data:www-data ["requirements.txt", "/var/www/djing2"]
RUN ["pip", "install", "--no-cache-dir", "-r", "/var/www/djing2/requirements.txt"]
RUN ["apk", "del", "-r", "gcc", "git", "make"]

EXPOSE 8000

COPY --chown=www-data:www-data ["manage.py", "create_initial_user.py", "uwsgi_djing2.ini", "ipt_linux_agent.py", "/var/www/djing2/"]
COPY --chown=www-data:www-data ["apps", "/var/www/djing2/apps"]

WORKDIR /var/www/djing2

USER www-data

CMD ./manage.py migrate \
    && ./manage.py loaddata initial_data \
    # && ./manage.py compilemessages -l ru \
    # && ./manage.py shell -c "from create_initial_user import *; make_initial_user()"
    #&& exec uwsgi --ini /var/www/djing2/uwsgi_djing2.ini
    #&& exec uvicorn fastapi_app:app --host 0.0.0.0 --port 8000 --workers 8
    && exec uvicorn fastapi_app:app --host 0.0.0.0 --port 8000 --reload

