#!/bin/bash
# Close k3s
function stop_container {
        supervisorctl stop k3s
        docker ps | awk '{print $1}' | sed '1d' | xargs docker stop
        exit 0
}
# Function to stop execution after receiving the signal
trap stop_container SIGTERM

# unzip the image
 while true; do
        docker load -i /app/ui/rainbond.tar
 if [ $? -eq 0 ]; then
 break
 fi
 done

#Start K3s 

/usr/local/bin/k3s server --docker --disable traefik --data-dir /app/data/k3s
