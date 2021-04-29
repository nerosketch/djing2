FROM freeradius/freeradius-server:latest-alpine

LABEL maintainer="nerosketch@gmail.com"

COPY raddb/ /etc/raddb/

EXPOSE 18120/udp 18130/udp

# CMD ["radiusd", "-X", "-d", "/etc/raddb"]