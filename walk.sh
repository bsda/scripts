#!/bin/bash
export 'PS4=+$me.$LINENO '
export DISPLAY=:0

LOCKFILE=/tmp/walk.lock

if [ -e ${LOCKFILE} ] && kill -0 `cat ${LOCKFILE}`; then
    echo "already running"
    exit
fi

trap "rm -f ${LOCKFILE}; exit" INT TERM EXIT
echo $$ > ${LOCKFILE}


#1=NO (SLEEP 5 minutes and run again)
#0=YES (EXIT LOCK SCREEN)
#5=TIMEOUT (EXIT AND LOCK SCREEN)

running=$(gnome-screensaver-command -q)
if [[ $running =~ " active" ]]
then
    echo "Already locked"
    exit 0
fi

hour=$(date +%H)
if [[ $hour -ge 14 ]] &&  [[ $hour -le 15 ]]
then 
    msg="GO BRUSH YOUR TEETH"
else
    msg="GO FOR A WALK"
fi

gone_for_a_walk="false"

while [[ $gone_for_a_walk == "false" ]]
do
    $(sleep 1 && wmctrl -F -a Question -b add,above)&
    zenity --question --timeout 20 --text="$msg" --display=:0
    error=$?
    if [[ $error -eq 0 ]]
    then
        gone_for_a_walk="true"
        gnome-screensaver-command -m "GONE FOR A WALK" -a -l
        #echo "YES LOCK"
    elif [[ $error -eq 5 ]]
    then
        gone_for_a_walk="true"
        gnome-screensaver-command -m "GONE FOR A WALK" -a -l
        #echo "TIMEOUT LOCK"
    elif [[ $error -eq 1 ]]
    then
        #echo "sleep and run command again"
        sleep 60
    fi
done
