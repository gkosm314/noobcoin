import re
import pathlib
import pandas as pd
from matplotlib import pyplot as plt


def avg(l):
    return sum(l)/len(l)

def calc_single_c_d_n(capasity, difficulty, total_nodes):
    '''Return throughput and blocktime for a given capasity, difficulty and total_nodes'''
    
    throughput_all_nodes = []
    block_time_all_nodes = []

    a = pathlib.Path("auto_script/10nodes/results")
    for filename in a.rglob("*.txt"):
        regex_filename = r"node(\d-\d)_c(\d+)_d(\d+)_n(\d+)"
        nodeid, c, d, n = re.findall(regex_filename, str(filename))[0]

        if not (int(c) == capasity and int(d) == difficulty and int(n)==total_nodes):
            continue
        # print(filename)
        f = open(filename, 'r')
        raw_file = f.read()
        f.close()

        regex1 = r"attach block: block time: \d+.\d+ current time:(\d+.\d+)\n" 
        regex2 = r"completed resolution at current time:(\d+.\d+)\n"
        block_matches = [float(t) for t in re.findall(regex1, raw_file) + re.findall(regex1, raw_file)]

        regex_start_time = r"starting time: (\d+.\d+)\n" 
        start_time = float(re.findall(regex_start_time, raw_file)[0])
        
        end_time = max(block_matches)

        with open(filename, 'r') as f:
            blocks_in_blockchain = int(f.readlines()[-1])
        
        throughput = blocks_in_blockchain*int(c)/(end_time-start_time)
        if end_time-start_time < 0:
            continue
        
        regex_create_time = "creating new block at time: (\d+.\d+)\n"
        create_matches = [float(t) for t in re.findall(regex_create_time, raw_file)]
        time_between_block_creations = [j-i for i, j in zip(create_matches[:-1], create_matches[1:])]
        avg_block_time_per_node = avg(time_between_block_creations)

        throughput_all_nodes.append(throughput)
        block_time_all_nodes.append(avg_block_time_per_node)

    return (avg(throughput_all_nodes), avg(block_time_all_nodes))


cap = [1,5,10]
throughput_d4 = []
blocktime_d4 = []

throughput_d5 = []
blocktime_d5 = []

for c in cap:
    t, b = calc_single_c_d_n(c, 4, 10)
    throughput_d4.append(t)
    blocktime_d4.append(b)

    t, b = calc_single_c_d_n(c, 5, 10)
    throughput_d5.append(t)
    blocktime_d5.append(b)

    # print(throughput)

##########################
# Throughput vs capasity #
##########################
fig, ax = plt.subplots(figsize=(6, 5), dpi=80)
plt.plot(cap, throughput_d4, "--*", label="d=4")
plt.plot(cap, throughput_d5, "--*", label="d=5")
ax.legend()
# plt.title("a")
plt.xlabel("Block capacity")
plt.ylabel("Throughput (transactions/sec)")
#show axis ticks only where points are
ax.set_xticks(cap)
ax.set_yticks(throughput_d4+throughput_d5)


##########################
# Block time vs capasity #
##########################
fig, ax = plt.subplots(figsize=(6, 5), dpi=80)
plt.plot(cap, blocktime_d4, "--*", label="d=4")
plt.plot(cap, blocktime_d5, "--*", label="d=5")
ax.legend()
# plt.title("a")
plt.xlabel("Block capacity")
plt.ylabel("Block time (sec)")
#show axis ticks only where points are
ax.set_xticks(cap)
ax.set_yticks(blocktime_d4+blocktime_d5)




plt.show()
