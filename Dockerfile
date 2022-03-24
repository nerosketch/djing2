FROM python:3.9

LABEL maintainer="nerosketch@gmail.com"

ENV PYTHONUNBUFFERED=1
ENV PYTHONOPTIMIZE=1
ENV PYTHONPATH="/var/www/djing2/apps:/var/www/djing2:/usr/local/lib/python3.9/site-packages:/usr/local/lib/python3.9/lib-dynload:/usr/local/lib/python3.9"

RUN ["apt-get", "update"]
RUN ["apt-get", "install", "-y", "python3-psycopg2", "libsnmp-dev", "arping", "gcc", "gettext", "telnet", "uwsgi", "uwsgi-plugin-python3", "--no-install-recommends"]
RUN mkdir -p /var/www/djing2/media \
    && touch /var/www/djing2/touch_reload \
    && chown -R www-data. /var/www/djing2

COPY --chown=www-data:www-data ["requirements.txt", "/var/www/djing2"]
RUN ["pip", "install", "--no-cache-dir", "-r", "/var/www/djing2/requirements.txt"]
RUN ["apt-get", "purge", "-y", "--auto-remove", "gcc"]

EXPOSE 3031 1717

COPY --chown=www-data:www-data ["manage.py", "create_initial_user.py", "uwsgi_djing2.ini", "ipt_linux_agent.py", "/var/www/djing2/"]
COPY --chown=www-data:www-data ["apps", "/var/www/djing2/apps"]

WORKDIR /var/www/djing2

USER www-data

CMD ./manage.py migrate \
    && ./manage.py loaddata initial_data \
    # && ./manage.py compilemessages -l ru \
    # && ./manage.py shell -c "from create_initial_user import *; make_initial_user()"
    && exec uwsgi --ini /var/www/djing2/uwsgi_djing2.ini
