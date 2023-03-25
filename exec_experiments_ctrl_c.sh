#!/bin/bash

mkdir -p results/auto_script/logs/

zzz_time=10 # in secs
n=5

PIDs=()
trap ctrl_c INT
function ctrl_c() {
    echo ${PIDs[*]}
    for i in ${!PIDs[@]}; do
        if (($i != 'x')); then 
            echo "node$i kill ${PIDs[$i]}"
        fi
    done
    exit 0
}


schedule_exec_kill_cp() {
    local vm_num=$1
    local role=$2 
    local PID=$(ssh node$vm_num "source venv/bin/activate;cd noobcoin; python3.7 -u network_wrapper5.py $role $cap $d $n > results_c$cap\_d$d\_n$n.txt & echo \$!")
    # echo $PID
    sleep $zzz_time
    ssh node$vm_num "kill ${PID}"  
    scp node$vm_num:~/noobcoin/results_c$cap\_d$d\_n$n.txt results/auto_script/node$vm_num\_c$cap\_d$d\_n$n.results 
    scp node$vm_num:~/noobcoin/logfile results/auto_script/logs/node$vm_num\_c$cap\_d$d\_n$n.log
}

for d in 4 
do
for cap in 1 
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