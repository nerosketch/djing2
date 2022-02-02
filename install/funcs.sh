
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


gen_secret() {
  local len="$1"
  head -c "$len" /dev/urandom | base64
}
