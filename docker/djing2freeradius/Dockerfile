FROM freeradius/freeradius-server:latest-alpine

LABEL maintainer="nerosketch@gmail.com"

COPY raddb/ /etc/raddb/

EXPOSE 1812/udp 1813/udp

# CMD ["radiusd", "-X", "-d", "/etc/raddb"]