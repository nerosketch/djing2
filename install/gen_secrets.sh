#!/bin/bash

PATH=/bin:/usr/local/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin


if [ ! -f /etc/debian_version ]; then
  echo "Script required Debian"
  exit 0
fi

source "$(dirname $0)/funcs.sh"

gen_secret 20 > ./secrets/API_AUTH_SECRET
gen_secret 50 > ./secrets/DJANGO_SECRET_KEY
gen_secret 32 > ./secrets/FIELD_ENCRYPTION_KEY
gen_secret 20 > ./secrets/RADIUS_SECRET
gen_secret 20 > ./secrets/SORM_EXPORT_FTP_PASSWORD
gen_secret 20 > ./secrets/VAPID_PUBLIC_KEY
gen_secret 20 > ./secrets/VAPID_PRIVATE_KEY
gen_secret 20 > ./secrets/POSTGRES_PASSWORD
gen_secret 20 > ./secrets/RADIUS_SECRET

