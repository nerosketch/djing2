#!/bin/bash

PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
DIR="/var/www/djing2"

cd "$DIR"
cmd=$1

uwsgi --pyshell-oneshot --chdir="$DIR/apps" --master --python "$DIR/manage.py" --pyargv="$cmd"

