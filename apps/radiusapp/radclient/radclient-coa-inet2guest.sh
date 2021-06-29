#!/bin/bash

#
# This script already running from async manager.
# No need to run radclient from another process.
#
# INFO: This file only example, change it for your case.
#

PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

client_radius_uname="$1"
#service_speed_in="$2"
#service_speed_out="$3"
#service_speed_in_burst="$4"
#service_speed_out_burst="$5"

echo "User-Name=${client_radius_uname},
      ERX-Service-Deactivate=SERVICE-INET,
      ERX-Service-Activate:1=SERVICE-GUEST" | radclient -sx 127.0.0.1 coa testing123
