#!/bin/bash 
until python3 -m bot; do
    echo "Bot crashed with exit code $?. Respawning.." >&2
    sleep 1
done