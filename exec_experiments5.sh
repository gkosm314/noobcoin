#!/bin/bash

mkdir -p auto_script/5nodes/logs/
mkdir -p auto_script/5nodes/results/
cat /dev/null > .pids

zzz_time=100 # in secs
n=5

function zzz_sleep() {
    zzz_secs=$1
    if $2 
    then
        while [ $zzz_secs -gt 0 ]; do
            echo -ne "  $zzz_secs\033[0K\r"
            sleep 1
            : $((zzz_secs--))
        done
    else
        sleep $zzz_secs
    fi
    
}

trap ctrl_c INT
function ctrl_c() {
    echo "killing all remote processes..."
    chmod +x .pids
    source .pids
    pkill bash # kill all the backgrounded subprocesses
    exit 0
}

schedule_exec_kill_cp() {
    local vm_num=$1
    local role=$2 
    local do_print=$3
    local PID=$(ssh node$vm_num "source venv/bin/activate;cd noobcoin; python3.7 -u network_wrapper5.py $role $cap $d $n > results.txt & echo \$!")
    # local PID=$(ssh node$vm_num "source venv/bin/activate;python3.7 -u long_running.py $role > mylog & echo \$!")
    echo ssh node$vm_num \"kill ${PID}\" >> .pids
    zzz_sleep $zzz_time $do_print
    ssh node$vm_num "kill ${PID}"  
    scp node$vm_num:~/noobcoin/results.txt auto_script/5nodes/results/node$vm_num\_c$cap\_d$d\_n$n.txt #_c$cap\_d$d\_n$n
    scp node$vm_num:~/noobcoin/logfile auto_script/5nodes/logs/node$vm_num\_c$cap\_d$d\_n$n.log
}

for d in 4 5
do
    for cap in 1 5 10
    do  
        echo "executing capacity $cap, difficulty $d..."
        for vm_num in 1 2 3 4 5
        do
            if ((vm_num == 1))
            then
                role="bootstrap"
                schedule_exec_kill_cp $vm_num $role false &
                sleep 1 #give some slack to bootstrap
            elif ((vm_num == 5))
            then
                role="node$vm_num"
                schedule_exec_kill_cp $vm_num $role true # keep running in foreground
            else
                role="node$vm_num"
                schedule_exec_kill_cp $vm_num $role false &
            fi
        done
        echo "done"
        cat /dev/null > .pids
        sleep 15
    done
done