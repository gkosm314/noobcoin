#!/bin/bash

mkdir -p auto_script/10nodes/logs/
mkdir -p auto_script/10nodes/results/
cat /dev/null > .pids

zzz_time=60 # in secs
n=10

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
    echo "\nkilling all remote processes..."
    chmod +x .pids
    source .pids
    pkill bash # kill all the backgrounded subprocesses
    exit 0
}

schedule_exec_kill_cp() {
    local vm_num=$1
    local role=$2 
    local cpu=$3
    local do_print=$4
    local PID=$(ssh node$vm_num "source venv/bin/activate;cd noobcoin; taskset --cpu-list $cpu python3.7 -u network_wrapper10.py $role $cap $d 10 $cpu > results$cpu.txt & echo \$!")
    # local PID=$(ssh node$vm_num "source venv/bin/activate;taskset --cpu-list $cpu python3.7 -u long_running.py $role > mylog & echo \$!")
    echo ssh node$vm_num \"kill ${PID}\" >> .pids
    zzz_sleep $zzz_time $do_print
    ssh node$vm_num "kill ${PID}"  
    scp node$vm_num:~/noobcoin/results$cpu.txt auto_script/10nodes/results/node$vm_num-$cpu\_c$cap\_d$d\_n10.txt #_c$cap\_d$d\_n$n
    scp node$vm_num:~/noobcoin/logfile$cpu auto_script/10nodes/logs/node$vm_num-$cpu\_c$cap\_d$d\_n10.log
}

for d in 4 5
do
    for cap in 1 5 10
    do  
        echo "[$(date +"%T")] executing capacity $cap, difficulty $d..."
        for vm_num in 1 2 3 4 5
        do
            case $vm_num in
                1)
                    schedule_exec_kill_cp $vm_num "bootstrap" 0 false&
                    sleep 3 # give some slack to bootstrap
                    schedule_exec_kill_cp $vm_num "node1" 1 false&
                    ;;
                2)
                    schedule_exec_kill_cp $vm_num "node2" 0 false&
                    sleep 1
                    schedule_exec_kill_cp $vm_num "node3" 1 false&
                    ;;

                3)
                    schedule_exec_kill_cp $vm_num "node4" 0 false&
                    sleep 1
                    schedule_exec_kill_cp $vm_num "node5" 1 false&
                    ;;

                4)
                    schedule_exec_kill_cp $vm_num "node6" 0 false&
                    sleep 1
                    schedule_exec_kill_cp $vm_num "node7" 1 false&
                    ;;
                5)
                    schedule_exec_kill_cp $vm_num "node8" 0 false&
                    sleep 1
                    schedule_exec_kill_cp $vm_num "node9" 1 true # keep running in foreground
                    ;;
            esac
        done
        echo "done"
        cat /dev/null > .pids
        sleep 15
    done
done