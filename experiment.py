from network_wrapper import *
import config
import re
import logging

logging.basicConfig(level=logging.DEBUG, filename="logfile", filemode="w+",
    format="%(asctime)-15s %(levelname)-8s %(message)s")

role = sys.argv[1]
if role == "bootstrap":
    is_bootstrap = True
    node_ip = config.BOOTSTRAP_IP
    node_port = config.BOOTSTRAP_PORT

elif role == "node":
    is_bootstrap = False
    node_ip = config.NODE_IP
    node_port = config.NODE_PORT
    
node_wrapper = node_network_wrapper(node_ip, node_port, config.BOOTSTRAP_IP, config.BOOTSTRAP_PORT, config.TOTAL_NODES, is_bootstrap)
print("end of init phase")
n = node_wrapper.node        


#open and parse the input file:    
input_filename = f'transactions/{config.TOTAL_NODES}nodes/transactions{n.node_id}.txt'

regex = r"^id(\d) (\d+)"
p = re.compile(regex)
transactions = []
with open(input_filename, "r") as f:
    for line in f:
        matches = re.findall(regex, line)
        recipient_node_id, amount = matches[0]
        
        recipient_node_id = int(recipient_node_id)
        amount = int(amount)
        transactions.append((recipient_node_id, amount))

#execute the transactions:
for (recipient_node_id, amount) in transactions:
    n.create_transaction(recipient_node_id, amount)

# n.view_transactions()
