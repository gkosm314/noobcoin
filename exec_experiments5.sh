#!/bin/bash

mkdir -p results/auto_script/logs/
cat /dev/null > .pids

zzz_time=367 # in secs
n=5

trap ctrl_c INT
function ctrl_c() {
    echo "killing all remote processes..."
    chmod +x .pids
    source .pids
    exit 0
}

schedule_exec_kill_cp() {
    local vm_num=$1
    local role=$2 
    local PID=$(ssh node$vm_num "source venv/bin/activate;cd noobcoin; python3.7 -u network_wrapper5.py $role $cap $d $n > results.txt & echo \$!")
    echo ssh node$vm_num \"kill ${PID}\" > .pids
    sleep $zzz_time
    ssh node$vm_num "kill ${PID}"  
    scp node$vm_num:~/noobcoin/results.txt results/auto_script/node$vm_num\_c$cap\_d$d\_n$n.results #_c$cap\_d$d\_n$n
    scp node$vm_num:~/noobcoin/logfile results/auto_script/logs/node$vm_num\_c$cap\_d$d\_n$n.log
}

for d in 4 
do
for cap in 1 5 10
do  
    echo "executing capacity $cap, difficulty $d..."
    for vm_num in 1 2 3 4 5
    do
        if ((vm_num == 1))
        then
            role="bootstrap"
            schedule_exec_kill_cp $vm_num $role &
        elif ((vm_num == 5))
        then
            role="node$vm_num"
            schedule_exec_kill_cp $vm_num $role # keep running in foreground
        else
            sleep 3 #give some slack to bootstrap
            role="node$vm_num"
            schedule_exec_kill_cp $vm_num $role &
        fi
    done
done
done