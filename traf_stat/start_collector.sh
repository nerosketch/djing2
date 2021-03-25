#!/usr/bin/env bash

PATH=/bin:/usr/local/sbin:/usr/local/bin:/usr/bin

tmpdir='/tmp/ft'
mkdir -p $tmpdir
rm -f $tmpdir/*

nfcapd -D -wt 60 -p 9975 -l $tmpdir -x './on_new_dump.sh %d/%f'
