#!/bin/bash

zzz_time=10 # in secs
cap=1
d=4
n=5


trap ctrl_c INT
function ctrl_c() {
    echo "hi"
    while read -r word1 word2; do
        echo "$word1"
        echo "$word2"
    done <pids.txt
    exit 0
}

sleep 100