#!/bin/bash

#
# This script already running from async manager.
# No need to run radclient from another process.
#
# INFO: This file only example, change it for your case.
#


PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

client_radius_uname="$1"

echo "User-Name=${client_radius_uname}" | radclient -q 127.0.0.1 disconnect testing123
