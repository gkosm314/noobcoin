import sys
import logging
import config

from network_wrapper5 import *

logging.basicConfig(level=logging.DEBUG, filename="logfile", filemode="w+",
    format="%(asctime)-15s %(levelname)-8s %(message)s")

help_msg = ''' 
t ID AMOUNT - create a transaction that will transfer AMOUNT coins from this node to the node with id = ID
view		- prints the contents of the last block in the blockchain
balance 	- prints the current balance of this node according to the blockchain
'''


def parse_cmdline():
    while True:
        cmd = input(">> ").split(" ")
        
        if cmd == []:
            pass
        elif cmd[0] == "t" and len(cmd) == 3:
            try:
                recipient_id = int(cmd[1])
                amount = int(cmd[2])
            except:
                print("Wrong arguments.")
            else:
                n.create_transaction(recipient_id,amount)
                print(f"create {recipient_id} {amount}")

        elif cmd[0] == "view" and len(cmd) == 1:
            n.view_transaction()
            print("view...")

        elif cmd[0] == "balance"  and len(cmd) == 1:
            n.wallet_balance(n.node_id)
            print("balance...")
        elif cmd[0]  == "help":
            print(help_msg)
        else:
            print("Wrong arguments")


role = sys.argv[1]
if role == "bootstrap":
    ip = config.BOOTSTRAP_IP 
    port = config.BOOTSTRAP_PORT
    is_bootstrap = True
elif role == "node":
    ip = config.NODE_IP
    port = config.NODE_PORT
    is_bootstrap = False
else:
    print(help_msg)
    exit()

print("Initializing noobcoin node...")
wrapper = node_network_wrapper(ip, port, config.NODE_IP, config.BOOTSTRAP_PORT, config.TOTAL_NODES, is_bootstrap)
n = wrapper.node    
parse_cmdline()





















# if role == "bootstrap":
#     logging.info("end of init phase")
#     # node_wrapper = node_network_wrapper(NODE_IP, NODE_PORT, config.BOOTSTRAP_IP, config.BOOTSTRAP_PORT)

#     n = bootstrap_wrapper.node
#     time.sleep(2)
#     while 1:
#         x = input("> ")
#         if x == "t":
#             print("create tx command given by prompt")
#             #n.create_transaction(1, 100)
#         else:
#             print("helpme")
    
#     n.create_transaction(2, 100)
#     n.create_transaction(3, 100)        
#     test_func(n)


# elif role == "node1":
#     node_wrapper = node_network_wrapper(config.NODE_IP, config.NODE_PORT, config.BOOTSTRAP_IP, config.BOOTSTRAP_PORT, config.TOTAL_NODES, False)
#     logging.info("end of init phase")
#     n = node_wrapper.node        
#     time.sleep(10)
#     n.create_transaction(3, 1)
#     n.create_transaction(0, 1)
#     n.create_transaction(2, 1)
#     n.create_transaction(3, 1)
#     n.create_transaction(2, 1)
#     test_func(n)


# elif role == "node2":
#     node_wrapper = node_network_wrapper(config.NODE_IP, config.NODE_PORT+1, config.BOOTSTRAP_IP, config.BOOTSTRAP_PORT, config.TOTAL_NODES, False)
#     logging.info("end of init phase")
#     n = node_wrapper.node
#     time.sleep(10)
#     n.create_transaction(1, 1000)           
#     n.create_transaction(1, 1)
#     n.create_transaction(3, 1)
#     n.create_transaction(0, 1)
#     n.create_transaction(1, 1)
#     n.create_transaction(1, 1) 
#     n.create_transaction(0, 1)
#     n.create_transaction(1, 1)
#     test_func(n)


# elif role == "node3":
#     node_wrapper = node_network_wrapper(config.NODE_IP, config.NODE_PORT+2, config.BOOTSTRAP_IP, config.BOOTSTRAP_PORT, config.TOTAL_NODES, False)
#     logging.info("end of init phase")
#     n = node_wrapper.node
#     time.sleep(10)    
#     n.create_transaction(0, 1)
#     n.create_transaction(1, 1)
#     n.create_transaction(1, 1000)
#     n.create_transaction(2, 1)
#     n.create_transaction(1, 1)
#     test_func(n)