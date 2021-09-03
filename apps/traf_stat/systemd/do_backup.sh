#!/bin/bash
PATH=/bin:/usr/local/bin:/usr/bin:/usr/local/sbin:/usr/sbin

cd /var/backups

file="djing`date "+%Y-%m-%d_%H.%M.%S"`.sql"

/bin/su postgres -c "/usr/bin/pg_dump -T traf_cache -T 'traf_archive_*' -f /tmp/${file} djing2_prod_db_name"
mv /tmp/$file ./
gzip -9 $file

chmod 400 $file.gz
chown $USER. $file.gz

# удаляем старые
find . -name "djing20??-??-??_??.??.??.sql.gz" -mtime +30 -type f -delete
