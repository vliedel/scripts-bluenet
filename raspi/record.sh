#!/bin/bash

cd dev/scripts-bluenet

while true; do
        python3 record/record-voltage.py &
        last_pid=$!
        sleep 600
        kill -SIGINT $last_pid
        sleep 1
        kill -SIGINT $last_pid
done

