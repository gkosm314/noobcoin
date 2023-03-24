#!/bin/bash

zzz_time=10 # in secs
cap=1
d=4
n=5

# trap ctrl_c INT
# function ctrl_c() {
#     echo "${arr[@]}"
#     for i in ${!PIDs[@]}; do
#         if (($i != 'x')); then 
#             echo "node$i kill ${PIDs[$i]}"
#         fi
#     done
#     exit 0
# }

# PIDs=('x' 'p' 'p' 'p' 'p' 'p') # dummy values (one extra)

exec_and_kill() {
    # PID=$(ssh node$vm_num "source venv/bin/activate;cd noobcoin; python3.7 -u network_wrapper5.py $role $cap $d $n > results_c$cap\_d$d\_n$n.txt & echo \$!")
    # 
    local vm_num=$1
    local role=$2 
    local PID=$(ssh node$vm_num "python3.7 -u long_running.py $role > mylog_$role & echo \$!")
    echo $PID
    sleep $zzz_time
    ssh node$vm_num "kill ${PID}"  
    scp node$vm_num:~/mylog_$role results/auto_script #change the file here! noobcoin/...
}


for vm_num in 1 2 3 4 5
do
    if ((vm_num == 1))
    then
        role="bootstrap"
        exec_and_kill $vm_num $role &
    elif ((vm_num == 5))
    then
        sleep 3 #give some slack to bootstrap
        role="node"
        exec_and_kill $vm_num $role # keep running in foreground
    else
        sleep 3 
        role="node"
        exec_and_kill $vm_num $role &
    fi
done