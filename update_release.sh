#!/bin/bash

PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

dock=$(which docker)
if [ $? -eq 1 ]; then
  echo "docker not found. Check if it is installed."
  exit 1
fi

docker login && \
docker build -t nerosketch/djing2-app:latest . && \
docker push nerosketch/djing2-app:latest
