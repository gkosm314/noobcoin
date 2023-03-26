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

    a = pathlib.Path("auto_script/")
    for filename in a.rglob(f"*_c{capasity}_d{difficulty}_n{total_nodes}.txt"):
        regex_filename = r"node([\d-]+)_c(\d+)_d(\d+)_n(\d+)"
        nodeid, c, d, n = re.findall(regex_filename, str(filename))[0]

        # if not (int(c) == capasity and int(d) == difficulty and int(n)==total_nodes):
        #     continue
    
        print(filename)
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
        create_matches = [start_time]+[float(t) for t in re.findall(regex_create_time, raw_file)]
        time_between_block_creations = [j-i for i, j in zip(create_matches[:-1], create_matches[1:])]
        if time_between_block_creations == []:
            continue # no blocks where created
        avg_block_time_per_node = avg(time_between_block_creations)

        throughput_all_nodes.append(throughput)
        block_time_all_nodes.append(avg_block_time_per_node)

    return (avg(throughput_all_nodes), avg(block_time_all_nodes))

def calc_block_time(c, d, n):
    _, b = calc_single_c_d_n(c, d, n)
    return b

def calc_throughput(c, d, n):
    t, _ = calc_single_c_d_n(c, d, n)
    return t


cap = [1,5,10]

##########################################################
##                    FOR 5 NODES                       ##
##########################################################

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


#------------------------|
# Throughput vs capasity |
#------------------------|
fig, ax = plt.subplots()
plt.plot(cap, throughput_d4, "--*", label="d=4")
plt.plot(cap, throughput_d5, "--*", label="d=5")
ax.legend()
plt.title("Throughput vs capacity for 5 node system")
plt.xlabel("Block capacity")
plt.ylabel("Throughput (transactions/sec)")
ax.set_xticks(cap)
ax.set_yticks(throughput_d4+throughput_d5)


#------------------------|
# Block time vs capasity |
#------------------------|
fig, ax = plt.subplots() #figsize=(6, 5), dpi=80
plt.plot(cap, blocktime_d4, "--*", label="d=4")
plt.plot(cap, blocktime_d5, "--*", label="d=5")
ax.legend()
plt.title("Block time vs capacity for 5 node system")
plt.xlabel("Block capacity")
plt.ylabel("Block time (sec)")
ax.set_xticks(cap)
ax.set_yticks(blocktime_d4+blocktime_d5)



##########################################################
##                    FOR 10 NODES                      ##
##########################################################

#------------------------|
# Throughput vs nodes    |
#------------------------|

fig, ax = plt.subplots() #figsize=(6, 5), dpi=80
plt.plot([5, 10], [calc_throughput(1, 4, 5), calc_throughput(1, 4, 10)], "--*", label="c=1, d=4")
plt.plot([5, 10], [calc_throughput(5, 4, 5), calc_throughput(5, 4, 10)], "--*", label="c=5, d=4")
plt.plot([5, 10], [calc_throughput(10, 4, 5), calc_throughput(10, 4, 10)], "--*", label="c=10, d=4")
plt.plot([5, 10], [calc_throughput(1, 5, 5), calc_throughput(1, 5, 10)], "--*", label="c=1, d=5")
plt.plot([5, 10], [calc_throughput(5, 5, 5), calc_throughput(5, 5, 10)], "--*", label="c=5, d=5")
plt.plot([5, 10], [calc_throughput(10, 5, 5), calc_throughput(10, 5, 10)], "--*", label="c=10, d=5")

ax.legend()
plt.title("Scaling of throughput")
plt.xlabel("Number of nodes")
plt.ylabel("Throughput (transactions/sec)")
ax.set_xticks([5,10])
# ax.set_yticks(blocktime_d4_c1+blocktime_d4_c5+blocktime_d4_c10+blocktime_d5_c1+blocktime_d5_c5+blocktime_d5_c10)


#------------------------|
# Block time vs nodes    |
#------------------------|

fig, ax = plt.subplots()
plt.plot([5, 10], [calc_block_time(1, 4, 5), calc_block_time(1, 4, 10)], "--*", label="c=1, d=4")
plt.plot([5, 10], [calc_block_time(5, 4, 5), calc_block_time(5, 4, 10)], "--*", label="c=5, d=4")
plt.plot([5, 10], [calc_block_time(10, 4, 5), calc_block_time(10, 4, 10)], "--*", label="c=10, d=4")
plt.plot([5, 10], [calc_block_time(1, 5, 5), calc_block_time(1, 5, 10)], "--*", label="c=1, d=5")
plt.plot([5, 10], [calc_block_time(5, 5, 5), calc_block_time(5, 5, 10)], "--*", label="c=5, d=5")
plt.plot([5, 10], [calc_block_time(10, 5, 5), calc_block_time(10, 5, 10)], "--*", label="c=10, d=5")

ax.legend()
plt.title("Scaling of block time")
plt.xlabel("Number of nodes")
plt.ylabel("Block time (sec)")
ax.set_xticks([5,10])
# ax.set_yticks(blocktime_d4_c1+blocktime_d4_c5+blocktime_d4_c10+blocktime_d5_c1+blocktime_d5_c5+blocktime_d5_c10)



plt.show()
