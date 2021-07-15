FROM nginx:alpine

LABEL maintainer="nerosketch@gmail.com"

COPY nginx.conf /etc/nginx/nginx.conf
COPY static /usr/share/nginx/html
COPY sites-enabled /etc/nginx/sites-enabled

EXPOSE 80 443
