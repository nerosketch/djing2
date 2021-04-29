#!/bin/bash

PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

opt="$1"
if [[ $opt == 'dev' ]]; then
  echo 'Install devel'
elif [[ $opt == 'prod' ]]; then
  echo 'Install production'
else
  echo 'Usage: ./install.sh <devel|prod>. Run it from "docker" sub directory'
  exit 1
fi

dc=$(which docker-compose)
if [ $? -eq 1 ]; then
  echo "docker-compose not found. Check if it is installed."
  exit 1
fi

#############################################
# Generate secrets, if it not generated yet
#############################################
cd ./secrets

gen_random_str(){
  fname="$1"
  allowed_chars="${2:-'A-Za-z0-9\!\@#\$%\^\&*(-_=+)'}"
  symbol_len="${3:-64}"
  if [[ ! -s "$fname" ]]; then
    tr -dc "$allowed_chars" < /dev/urandom | head -c "$symbol_len" > "$fname"
  fi
}

gen_random_str API_AUTH_SECRET
gen_random_str DJANGO_SECRET_KEY

if [[ ! -s FIELD_ENCRYPTION_KEY ]]; then
  touch FIELD_ENCRYPTION_KEY
fi

gen_random_str POSTGRES_PASSWORD "a-z0-9" "12"

gen_random_str VAPID_PUBLIC_KEY
gen_random_str VAPID_PRIVATE_KEY

# exit from ./secrets
cd ../
##################################################


# Build it
unlink docker-compose.yml
if [[ $opt == 'dev' ]]; then
  # Build it all devel
  ln -s docker-compose-devel.yml docker-compose.yml
  $dc build
elif [[ $opt == 'prod' ]]; then
  # Build it all production
  ln -s docker-compose-release.yml docker-compose.yml
  $dc build
fi
