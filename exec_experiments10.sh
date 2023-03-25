#!/bin/bash

mkdir -p results/auto_script/logs/
cat /dev/null > .pids

zzz_time=3600 # in secs
n=10

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
    local cpu=$3
    local PID=$(ssh node$vm_num "source venv/bin/activate;cd noobcoin; taskset --cpu-list $cpu python3.7 -u network_wrapper10.py $role $cap $d 10 > results$cpu.txt & echo \$!")
    echo ssh node$vm_num \"kill ${PID}\" > .pids
    sleep $zzz_time
    ssh node$vm_num "kill ${PID}"  
    scp node$vm_num:~/noobcoin/results$cpu.txt results/auto_script/node$vm_num-$cpu\_c$cap\_d$d\_n10.results #_c$cap\_d$d\_n$n
    scp node$vm_num:~/noobcoin/logfile results/auto_script/logs/node$vm_num-$cpu\_c$cap\_d$d\_n10.log
}

for d in 4 
do
for cap in 1 
do  
    echo "executing capacity $cap, difficulty $d..."
    for vm_num in 1 2 3 4 5
    do
        case $vm_num in
            1)
                schedule_exec_kill_cp $vm_num "bootstrap" 0 &
                sleep 3 # give some slack to bootstrap
                schedule_exec_kill_cp $vm_num "node1" 1 &
                ;;
            2)
                schedule_exec_kill_cp $vm_num "node2" 0 &
                schedule_exec_kill_cp $vm_num "node3" 1 &
                ;;

            3)
                schedule_exec_kill_cp $vm_num "node4" 0 &
                schedule_exec_kill_cp $vm_num "node5" 1 &
                ;;

            4)
                schedule_exec_kill_cp $vm_num "node6" 0 &
                schedule_exec_kill_cp $vm_num "node7" 1 &
                ;;
            5)
                schedule_exec_kill_cp $vm_num "node8" 0 &
                schedule_exec_kill_cp $vm_num "node9" 1 # keep running in foreground
                ;;
        esac
    done
done
done