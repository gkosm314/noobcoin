from network_wrapper import *
import config
import re
import logging

logging.basicConfig(level=logging.DEBUG, filename="logfile", filemode="w+",
    format="%(asctime)-15s %(levelname)-8s %(message)s")

role = sys.argv[1]

if role == "bootstrap":
    bootstrap_wrapper = node_network_wrapper(config.BOOTSTRAP_IP, config.BOOTSTRAP_PORT, config.BOOTSTRAP_IP, config.BOOTSTRAP_PORT, config.TOTAL_NODES, True)
    print("end of init phase")
    n = bootstrap_wrapper.node
    time.sleep(2)

elif role == "node":
    node_wrapper = node_network_wrapper(config.NODE_IP, config.NODE_PORT, config.BOOTSTRAP_IP, config.BOOTSTRAP_PORT, config.TOTAL_NODES, False)
    print("end of init phase")
    n = node_wrapper.node        
    time.sleep(15)

#open and parse the input file:    
input_filename = f'transactions/{config.TOTAL_NODES}nodes/transactions{n.node_id}.txt'

regex = r"^id(\d) (\d)"
p = re.compile(regex)

with open(input_filename, "r") as f:
    for line in f:
        matches = re.findall(regex, line)
        recipient_node_id, amount = matches[0]
        
        recipient_node_id = int(recipient_node_id)
        amount = int(amount)

        #execute the transactions:
        n.create_transaction(recipient_node_id, amount)

n.view_transactions()
