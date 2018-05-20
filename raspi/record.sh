#!/bin/bash

while true; do
        python3 ble/reset.py >> reset.log &
        sleep 60
        python3 record/record-voltage.py &
        last_pid=$!
        sleep 600
        kill -SIGINT $last_pid
        sleep 1
        kill -SIGINT $last_pid
done
