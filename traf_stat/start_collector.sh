#!/usr/bin/env bash

PATH=/bin:/usr/local/sbin:/usr/local/bin:/usr/bin

nfcapd -D -wt 60 -j -p 7463 -l ./incoming

# nfdump -r nfcapd.202101081045 -o "fmt:%ts*%te*%td*%pr*%flg*%in*%out*%pkt*%byt*%fl*%tos*%bps*%pps*%bpp*%sa*%sp*%xsa*%xsp*%da*%dp*%xda*%xdp"