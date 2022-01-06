FROM freeradius/freeradius-server:latest-alpine

LABEL maintainer="nerosketch@gmail.com"

RUN apk add python3 --no-cache --no-progress
RUN mkdir /opt/var/pool

COPY raddb/ /etc/raddb/

CMD ["radiusd", "-X", "-d", "/etc/raddb"]
