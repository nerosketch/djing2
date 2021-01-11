#!/bin/bash

if [ $# -eq 0 ]
then
  echo "No arguments supplied"
  exit
fi

parsetst() {
  fname="$1"
  echo 'INSERT INTO traf_cache (event_time, ip_addr, octets, packets) VALUES'
  nfdump -r $fname -O ipkg -Nq -A srcip -o 'fmt:%tsr;%sa;%pkt;%byt' 'src net 10.152.0.0/16 or src net 193.104.145.0/24' | while read -r line; do
    arrIn=(${line//;/ })
    echo "${c}(to_timestamp(${arrIn[0]}), '${arrIn[1]}', ${arrIn[3]}, ${arrIn[2]})"
    c=','
  done
  echo "ON CONFLICT (customer_id, ip_addr) DO UPDATE SET
    event_time = EXCLUDED.event_time,
    octets = EXCLUDED.octets,
    packets = EXCLUDED.packets;"
}

#parsetst $1
psql postgresql://postgres:2ekc3@127.0.0.1/djing2 -c "$(parsetst $1)"
