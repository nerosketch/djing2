#!/bin/bash

PATH=/bin:/usr/local/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin


if [ ! -f /etc/debian_version ]; then
  echo "Script required Debian"
  exit 0
fi


ask_var() {
  exec 3>&1
  local answer=$(dialog --title " $1 " --clear --inputbox "$2:" 16 51 2>&1 1>&3)
  if [ -n "$answer" ]; then
    eval "$3='$answer'"
    return 0
  fi
  echo 'password is required'
  exit 1
}


passw=''
ask_var "Пароль" "Введите пароль" passw

echo "Мой парль $passw"


exit


#while [ -n "$1" ]
#  do
#    case "$1" in
#      -p) echo "Password for db ***"
#          dbpassw="$2"
#          shift ;;
#      --) shift
#      break ;;
#    *) echo "$1 is not an option" ;;
#    esac
#  shift
#done



if [ -z "$dbpassw" ]; then
  read -s -p "Enter new password for database: " dbpassw
  if [ -z "$dbpassw" ]; then
    echo "Please type new password for database with parameter -p <password> and try again"
    exit 0;
  fi
else
  echo "Pass new password for db from parameter, use it!"
fi


apt -y update
apt -y upgrade

sleep 1
apt -y install $(cat debian_apt_requirements.txt)

sleep 3

mkdir -p /var/www
cd /var/www

mysql -u root -e "create database djing_db charset utf8 collate utf8_general_ci;"
mysql -u root -e "create user 'djinguser'@'localhost' identified by '${dbpassw}';"
mysql -u root -e "grant all privileges on djing_db.* to 'djinguser'@'localhost';"
mysql -u root -e "flush privileges;"

git clone --depth=1 https://github.com/nerosketch/djing2.git
cd djing2
python3 -m venv venv
source ./venv/bin/activate
pip install --upgrade pip
pip install wheel
export PYCURL_SSL_LIBRARY=openssl
pip install -r requirements.txt
cp -v apps/djing2/local_settings.py.example apps/djing2/local_settings.py
sed -i "s/'PASSWORD': 'password',/'PASSWORD': '${dbpassw}',/" djing2/local_settings.py
chmod +x ./manage.py
./manage.py migrate
./manage.py compilemessages -l ru
secret_key=`./manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key().replace(\"&\", \"@\"))"`
sed -i -r "s/^SECRET_KEY = '.+'$/SECRET_KEY = '${secret_key}'/" djing2/local_settings.py
./manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('+79781234567', 'admin', 'admin')"
deactivate

touch touch-reload
mkdir spooler
mkdir media
mkdir static

#cp install/robots.txt robots.txt
cp djing2.ini /etc/uwsgi/apps-available/djing2.ini
ln -s /etc/uwsgi/apps-available/djing2.ini /etc/uwsgi/apps-enabled/djing2.ini
cp install/nginx_server.conf /etc/nginx/sites-available/djing.conf
ln -s /etc/nginx/sites-available/djing.conf /etc/nginx/sites-enabled/djing.conf

# Extract executable for netflow dumping
cd agent/netflow
tar -xvzf djing_flow.tar.gz
cd ../../

chown -R www-data. /var/www/djing

# dirs
find . -type d \( -path ./venv -o -path ./src -o -path ./.git \) -prune -o -type d -exec chmod 750 {} \;
# files
find . -type d \( -path ./venv -o -path ./src -o -path ./.git \) -prune -o -type f -exec chmod 640 {} \;
# exec scripts
chmod 750 dhcp_lever.py manage.py periodic.py devapp/expect_scripts/dlink_DGS1100_reboot.exp agent/netflow/netflow_handler.py
chmod 750 agent/netflow/netflow_handler_slave.sh
chmod 400 djing/settings.py

rm /etc/nginx/sites-enabled/default
systemctl restart uwsgi
systemctl enable uwsgi
systemctl restart nginx
systemctl enable nginx


cp ./systemd_units/djing_celery.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable djing_celery.service
systemctl start djing_celery.service


echo -e "\n\nOpen your Djing on http://`hostname -i`/
Initial login and password admin admin\n"