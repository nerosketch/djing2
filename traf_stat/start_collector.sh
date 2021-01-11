#!/usr/bin/env bash

PATH=/bin:/usr/local/sbin:/usr/local/bin:/usr/bin

nfcapd -D -wt 60 -p 9975 -l ./ft -x './on_new_dump.sh %d/%f'
