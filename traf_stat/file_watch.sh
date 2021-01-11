#!/bin/bash

PATH=/bin:/usr/local/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin

TARGET=./incoming

tmpfile="/tmp/$(date '+%F%T%N').sql"

#inotifywait -m -e close_write --format "%f" $TARGET |

echo '/home/ns/nfcapd.202101110848' | while read -r fname; do
  echo 'INSERT INTO traf_cache (event_time, ip_addr, octets, packets) VALUES'
  #echo 'COPY traf_cache (event_time, ip_addr, octets, packets) FROM stdin;' > "$tmpfile"
  nfdump -r $fname -O ipkg -Nq -A srcip -o 'fmt:%tsr;%sa;%pkt;%byt;%bps;%bpp' 'src net 10.152.0.0/16 or src net 193.104.145.0/24' | while read -r line; do
    IFS=';' read -r date_first_seen srcip pkts bytes bps pps <<< `echo ${line//[[:blank:]]/}`
    # echo "date_first_seen '$date_first_seen' srcip '$srcip' pkts '$pkts' bytes '$bytes' bps '$bps' pps '$pps'"
    # echo "$(date -d @$date_first_seen '+%F %T.%N%:::z')\t${srcip}\t${bytes}\t${pkts}" >> "$tmpfile"
    echo "${c}('`date -d @$date_first_seen '+%F %T.%N%:::z'`', '$srcip', $bytes, $pkts)"
    c=','
  done
  echo "ON CONFLICT (customer_id, ip_addr) DO UPDATE SET
    event_time = EXCLUDED.event_time,
    octets = EXCLUDED.octets,
    packets = EXCLUDED.packets;"
  #psql postgresql://postgres:ps@127.0.0.1/djing -c "\i $tmpfile;"
#  rm "$tmpfile"
done
#