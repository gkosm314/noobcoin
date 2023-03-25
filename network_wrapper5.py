import requests
import json, jsonpickle
import sys 
import time
import pickle
from multiprocessing.pool import ThreadPool as Pool
import logging

import config
import node
import rest_api
import wallet


class node_network_wrapper:
    
    def __init__(self, node_ip_arg, node_port_arg, bootstrap_ip_arg, bootstrap_port_arg, total_nodes_arg, is_bootstrap):
        if not is_bootstrap:
            self.node = node.uninitialized_node()
        else:
            self.bootstrap_node = node.bootstrap_node(total_nodes_arg, bootstrap_ip_arg, bootstrap_port_arg)
            self.nodes_cnt = 1 # take into account bootstrap

        self.ip = node_ip_arg     
        self.port = node_port_arg 
        self.bootstrap_ip = bootstrap_ip_arg
        self.bootstrap_port = bootstrap_port_arg

        self.api_server = rest_api.node_api_server(self.ip, self.port, self)
        self.registration_completed = False 
        self.init_state_bcast_completed = False 

        self.api_server.run() 

        if not is_bootstrap:
            time.sleep(3)
            self.register()

            while 1:
                if self.registration_completed:
                    logging.info("node registered")
                    break
                time.sleep(1)
        else:
            while 1:
                if self.registration_completed: 
                    logging.info("All nodes registered")
                    break
                time.sleep(1)
        
            time.sleep(10)
            self.bcast_initial_state()
            
            self.node = self.bootstrap_node.produce_node()


    def register(self):
        '''send public key to bootstrap'''

        headers = {"Content-Type": "application/json; charset=utf-8"}
        
        payload_dict = {
            "my_public_key": self.node.wallet.public_key, 
            "my_ip": self.ip, 
            "my_port": self.port
        }
        payload_json = jsonpickle.encode(payload_dict, keys=True)
        
        req = requests.post(f"http://{self.bootstrap_ip}:{self.bootstrap_port}/register", headers=headers, data = payload_json)
        time.sleep(5)
        logging.info("i just registered myself and received", req.json())
        added_flag = req.json()['added']
        my_id = req.json()['assigned_id']
        if added_flag:
            self.node.set_node_id(my_id)  

    def save_net_info(self, public_keys_table_arg, ips_table_arg, genesis_block_arg):
        self.node.set_network_info_table(ips_table_arg)
        self.node.set_public_key_table(public_keys_table_arg)
        self.node.set_genesis_block(genesis_block_arg)

        self.node = self.node.produce_node()
        logging.info("saving info...")
        self.registration_completed = True

    def handle_incoming_tx(self, tx):
        self.node.receive_transaction(tx)

    def handle_incoming_block(self, b):
        self.node.receive_block(b, True)

    def get_blockchain_length(self):
        return len(self.node.current_blockchain)

    def get_blockchain_diff(self, hashes_list):
        i = 0
        if len(hashes_list) > len(self.node.current_blockchain):
            return ([], hashes_list[-1], len(hashes_list))
        while i < len(hashes_list):
            if hashes_list[i] == self.node.current_blockchain.chain[i].current_hash: 
                i+=1
            else:
                break
        diff = self.node.current_blockchain.chain[i:]
        # print(diff)
        if not diff: # diff is empty
            parent_hash = hashes_list[-1]
        else:    
            parent_hash = diff[0].previous_hash
        # print(parent_hash)
        return (diff, parent_hash, len(self.node.current_blockchain))

    def register_node(self, node_ip, node_port, node_public_key): 
        new_id = self.bootstrap_node.add_node(node_public_key, node_ip, node_port)
        
        if (new_id == -1): # node has been already added
            return {"added": False, "assigned_id": -1}

        self.nodes_cnt+=1

        if (self.nodes_cnt == self.bootstrap_node.number_of_nodes): # all nodes have registered
            self.registration_completed = True

        elif (self.nodes_cnt > self.bootstrap_node.number_of_nodes): # all nodes have registered
            return {"added": False, "assigned_id": -2}

        return {"added": True, "assigned_id": new_id}

    def bcast_initial_state(self):
        '''Broadcast to all the nodes the network info table, public key table and genesis block'''
        
        logging.info("broadcasting init state")
        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload_dict = {
            "public_keys_table": self.bootstrap_node.public_key_table, 
            "ips_table": self.bootstrap_node.network_info_table, 
            "genesis_block": self.bootstrap_node.g
        }
        payload_json = jsonpickle.encode(payload_dict, keys=True)
        
        def unicast(network_info_tuple_arg, payload_json_arg):
            ip, port = network_info_tuple_arg
            req = requests.post(f"http://{ip}:{port}/post_net_info", headers=headers, data = payload_json_arg)
            
        pool = Pool(self.bootstrap_node.number_of_nodes-1)
        
        for public_key, network_info_tuple in self.bootstrap_node.network_info_table.items():
            if public_key == self.bootstrap_node.wallet.public_key:
                # don't broadcast to self
                continue
        
            pool.apply_async(unicast, (network_info_tuple, payload_json,))

        pool.close()
        pool.join()
    
if __name__=="__main__":
    # logging.basicConfig(level=logging.WARNING)
    # flog = logging.getLogger('werkzeug')
    # #flog.setLevel(logging.ERROR)

    logging.basicConfig(level=logging.DEBUG, filename="logfile", filemode="w+",
    format="%(asctime)-15s %(levelname)-8s %(message)s")

    secs = 10

    role = sys.argv[1]

    # overwrite the config vars for automating exec
    cap_cmd_arg = int(sys.argv[2])
    diff_cmd_arg = int(sys.argv[3])
    total_nodes_cmd_arg = int(sys.argv[4])

    config.capacity = cap_cmd_arg
    config.difficulty = diff_cmd_arg
    config.TOTAL_NODES = total_nodes_cmd_arg

    def test_func(n):
        time.sleep(360)
        n.view_transactions()
        print(n.current_block.transactions)
        print(n.transactions_buffer)
        print(len(n.current_blockchain))
        

    print(f"running with d={config.difficulty}, cap={config.capacity}, total_nodes={config.TOTAL_NODES}")
    
    if role == "bootstrap":
        bootstrap_wrapper = node_network_wrapper(config.BOOTSTRAP_IP, config.BOOTSTRAP_PORT, config.BOOTSTRAP_IP, config.BOOTSTRAP_PORT, config.TOTAL_NODES, True)
        print("end of init phase")
        # node_wrapper = node_network_wrapper(NODE_IP, NODE_PORT, config.BOOTSTRAP_IP, config.BOOTSTRAP_PORT)

        n = bootstrap_wrapper.node
        time.sleep(2)
        n.create_transaction(1, 100)
        n.create_transaction(2, 100)
        n.create_transaction(3, 100)
        
        time.sleep(secs)
        print(f'starting time: {time.time()}')

        n.create_transaction(1, 7)
        n.create_transaction(2, 8)
        n.create_transaction(2, 7)
        n.create_transaction(2, 5)
        n.create_transaction(1, 5)
        n.create_transaction(3, 6)
        n.create_transaction(1, 6)
        n.create_transaction(4, 6)
        n.create_transaction(4, 3)
        n.create_transaction(4, 4)
        n.create_transaction(3, 8)
        n.create_transaction(4, 7)
        n.create_transaction(4, 8)
        n.create_transaction(2, 4)
        n.create_transaction(1, 2)
        n.create_transaction(3, 3)
        n.create_transaction(2, 3)
        n.create_transaction(1, 1)
        n.create_transaction(3, 1014)
        n.create_transaction(1, 7)
        n.create_transaction(4, 5)
        n.create_transaction(4, 1025)
        n.create_transaction(3, 10)
        n.create_transaction(3, 1)
        n.create_transaction(4, 9)
        n.create_transaction(2, 1)
        n.create_transaction(1, 3)
        n.create_transaction(2, 1035)
        n.create_transaction(4, 3)
        n.create_transaction(4, 2)
        n.create_transaction(4, 1)
        n.create_transaction(1, 2)
        n.create_transaction(4, 6)
        n.create_transaction(2, 1)
        n.create_transaction(3, 1)
        n.create_transaction(2, 5)
        n.create_transaction(4, 6)
        n.create_transaction(2, 4)
        n.create_transaction(3, 10)
        n.create_transaction(4, 9)
        n.create_transaction(4, 3)
        n.create_transaction(3, 2)
        n.create_transaction(2, 4)
        n.create_transaction(4, 2)
        n.create_transaction(3, 5)
        n.create_transaction(2, 1)
        n.create_transaction(2, 10)
        n.create_transaction(2, 7)
        n.create_transaction(3, 1055)
        n.create_transaction(3, 4)
        n.create_transaction(1, 6)
        n.create_transaction(2, 8)
        n.create_transaction(3, 2)
        n.create_transaction(2, 8)
        n.create_transaction(2, 1)
        n.create_transaction(1, 1)
        n.create_transaction(1, 6)
        n.create_transaction(3, 8)
        n.create_transaction(4, 8)
        n.create_transaction(3, 3)
        n.create_transaction(1, 7)
        n.create_transaction(1, 1)
        n.create_transaction(1, 5)
        n.create_transaction(4, 6)
        n.create_transaction(4, 6)
        n.create_transaction(2, 8)
        n.create_transaction(1, 5)
        n.create_transaction(1, 4)
        n.create_transaction(3, 6)
        n.create_transaction(1, 3)
        n.create_transaction(1, 6)
        n.create_transaction(1, 10)
        n.create_transaction(4, 7)
        n.create_transaction(3, 3)
        n.create_transaction(4, 10)
        n.create_transaction(2, 5)
        n.create_transaction(3, 8)
        n.create_transaction(3, 10)
        n.create_transaction(1, 8)
        n.create_transaction(3, 8)
        n.create_transaction(2, 1)
        n.create_transaction(4, 9)
        n.create_transaction(2, 5)
        n.create_transaction(4, 3)
        n.create_transaction(2, 2)
        n.create_transaction(3, 3)
        n.create_transaction(3, 5)
        n.create_transaction(4, 2)
        n.create_transaction(4, 5)
        n.create_transaction(3, 8)
        n.create_transaction(1, 4)
        n.create_transaction(1, 2)
        n.create_transaction(3, 6)
        n.create_transaction(1, 9)
        n.create_transaction(2, 4)
        n.create_transaction(2, 2)
        n.create_transaction(3, 3)
        n.create_transaction(1, 3)
        n.create_transaction(2, 1095)
        n.create_transaction(3, 6)
        test_func(n)        
       
    elif role == "node2":
        node_wrapper = node_network_wrapper(config.NODE_IP, config.NODE_PORT, config.BOOTSTRAP_IP, config.BOOTSTRAP_PORT, config.TOTAL_NODES, False)
        print("end of init phase")
        n = node_wrapper.node        
        time.sleep(secs)
        print(f'starting time: {time.time()}')

        n.create_transaction(3, 9)
        n.create_transaction(0, 6)
        n.create_transaction(3, 5)
        n.create_transaction(0, 2)
        n.create_transaction(4, 5)
        n.create_transaction(3, 1)
        n.create_transaction(2, 10)
        n.create_transaction(2, 8)
        n.create_transaction(0, 9)
        n.create_transaction(2, 7)
        n.create_transaction(2, 2)
        n.create_transaction(4, 10)
        n.create_transaction(2, 6)
        n.create_transaction(2, 5)
        n.create_transaction(0, 10)
        n.create_transaction(3, 3)
        n.create_transaction(4, 4)
        n.create_transaction(0, 3)
        n.create_transaction(4, 5)
        n.create_transaction(2, 9)
        n.create_transaction(0, 6)
        n.create_transaction(4, 10)
        n.create_transaction(3, 2)
        n.create_transaction(0, 7)
        n.create_transaction(2, 3)
        n.create_transaction(2, 10)
        n.create_transaction(4, 4)
        n.create_transaction(3, 6)
        n.create_transaction(2, 6)
        n.create_transaction(3, 8)
        n.create_transaction(3, 7)
        n.create_transaction(0, 4)
        n.create_transaction(3, 3)
        n.create_transaction(3, 9)
        n.create_transaction(3, 6)
        n.create_transaction(0, 6)
        n.create_transaction(0, 8)
        n.create_transaction(4, 10)
        n.create_transaction(3, 5)
        n.create_transaction(4, 10)
        n.create_transaction(2, 2)
        n.create_transaction(2, 5)
        n.create_transaction(4, 10)
        n.create_transaction(0, 5)
        n.create_transaction(2, 3)
        n.create_transaction(3, 7)
        n.create_transaction(3, 5)
        n.create_transaction(0, 4)
        n.create_transaction(3, 1)
        n.create_transaction(0, 3)
        n.create_transaction(0, 1)
        n.create_transaction(4, 2)
        n.create_transaction(3, 7)
        n.create_transaction(0, 6)
        n.create_transaction(3, 4)
        n.create_transaction(3, 9)
        n.create_transaction(3, 2)
        n.create_transaction(2, 2)
        n.create_transaction(2, 3)
        n.create_transaction(2, 9)
        n.create_transaction(3, 10)
        n.create_transaction(0, 3)
        n.create_transaction(2, 3)
        n.create_transaction(3, 10)
        n.create_transaction(0, 1)
        n.create_transaction(2, 10)
        n.create_transaction(0, 3)
        n.create_transaction(4, 7)
        n.create_transaction(2, 7)
        n.create_transaction(3, 5)
        n.create_transaction(4, 7)
        n.create_transaction(3, 10)
        n.create_transaction(0, 6)
        n.create_transaction(3, 10)
        n.create_transaction(2, 3)
        n.create_transaction(0, 3)
        n.create_transaction(2, 8)
        n.create_transaction(2, 2)
        n.create_transaction(0, 10)
        n.create_transaction(4, 4)
        n.create_transaction(2, 3)
        n.create_transaction(0, 9)
        n.create_transaction(2, 4)
        n.create_transaction(2, 9)
        n.create_transaction(4, 2)
        n.create_transaction(3, 2)
        n.create_transaction(0, 8)
        n.create_transaction(3, 3)
        n.create_transaction(0, 10)
        n.create_transaction(3, 2)
        n.create_transaction(4, 1)
        n.create_transaction(4, 6)
        n.create_transaction(0, 6)
        n.create_transaction(4, 7)
        n.create_transaction(4, 8)
        n.create_transaction(0, 1)
        n.create_transaction(3, 7)
        n.create_transaction(4, 1)
        n.create_transaction(0, 4)
        n.create_transaction(2, 5)
        n.create_transaction(3, 7)
        n.create_transaction(4, 1)
        n.create_transaction(0, 4)
        n.create_transaction(2, 5)
        test_func(n)
       
    elif role == "node3":
        node_wrapper = node_network_wrapper(config.NODE_IP, config.NODE_PORT+1, config.BOOTSTRAP_IP, config.BOOTSTRAP_PORT, config.TOTAL_NODES, False)
        print("end of init phase")
        n = node_wrapper.node
        time.sleep(secs)
        print(f'starting time: {time.time()}')

        n.create_transaction(4, 4)
        n.create_transaction(3, 6)
        n.create_transaction(0, 1035)
        n.create_transaction(4, 6)
        n.create_transaction(3, 1)
        n.create_transaction(1, 4)
        n.create_transaction(1, 3)
        n.create_transaction(1, 1025)
        n.create_transaction(0, 1)
        n.create_transaction(3, 6)
        n.create_transaction(0, 3)
        n.create_transaction(4, 3)
        n.create_transaction(4, 8)
        n.create_transaction(3, 3)
        n.create_transaction(3, 5)
        n.create_transaction(4, 9)
        n.create_transaction(3, 1065)
        n.create_transaction(0, 3)
        n.create_transaction(0, 1055)
        n.create_transaction(4, 2)
        n.create_transaction(3, 9)
        n.create_transaction(0, 8)
        n.create_transaction(1, 8)
        n.create_transaction(0, 3)
        n.create_transaction(0, 2)
        n.create_transaction(0, 3)
        n.create_transaction(3, 5)
        n.create_transaction(1, 9)
        n.create_transaction(1, 6)
        n.create_transaction(1, 7)
        n.create_transaction(3, 5)
        n.create_transaction(4, 7)
        n.create_transaction(0, 2)
        n.create_transaction(1, 4)
        n.create_transaction(1, 1)
        n.create_transaction(1, 3)
        n.create_transaction(1, 2)
        n.create_transaction(1, 1045)
        n.create_transaction(1, 6)
        n.create_transaction(1, 2)
        n.create_transaction(3, 6)
        n.create_transaction(1, 10)
        n.create_transaction(3, 5)
        n.create_transaction(0, 4)
        n.create_transaction(4, 7)
        n.create_transaction(0, 8)
        n.create_transaction(0, 8)
        n.create_transaction(4, 6)
        n.create_transaction(1, 7)
        n.create_transaction(4, 9)
        n.create_transaction(1, 2)
        n.create_transaction(1, 7)
        n.create_transaction(3, 7)
        n.create_transaction(3, 6)
        n.create_transaction(0, 7)
        n.create_transaction(4, 9)
        n.create_transaction(0, 4)
        n.create_transaction(4, 6)
        n.create_transaction(1, 10)
        n.create_transaction(4, 6)
        n.create_transaction(4, 8)
        n.create_transaction(3, 2)
        n.create_transaction(1, 10)
        n.create_transaction(0, 4)
        n.create_transaction(4, 8)
        n.create_transaction(1, 2)
        n.create_transaction(3, 8)
        n.create_transaction(0, 7)
        n.create_transaction(1, 3)
        n.create_transaction(0, 10)
        n.create_transaction(3, 2)
        n.create_transaction(3, 9)
        n.create_transaction(3, 4)
        n.create_transaction(0, 7)
        n.create_transaction(0, 5)
        n.create_transaction(3, 1)
        n.create_transaction(1, 6)
        n.create_transaction(0, 7)
        n.create_transaction(3, 5)
        n.create_transaction(0, 7)
        n.create_transaction(0, 10)
        n.create_transaction(1, 8)
        n.create_transaction(0, 4)
        n.create_transaction(4, 1)
        n.create_transaction(0, 4)
        n.create_transaction(0, 6)
        n.create_transaction(0, 6)
        n.create_transaction(4, 6)
        n.create_transaction(0, 9)
        n.create_transaction(1, 4)
        n.create_transaction(0, 9)
        n.create_transaction(4, 7)
        n.create_transaction(4, 7)
        n.create_transaction(1, 2)
        n.create_transaction(0, 8)
        n.create_transaction(3, 8)
        n.create_transaction(0, 6)
        n.create_transaction(1, 5)
        n.create_transaction(1, 6)
        n.create_transaction(1, 4)
        test_func(n)       

    elif role == "node4":
        node_wrapper = node_network_wrapper(config.NODE_IP, config.NODE_PORT+2, config.BOOTSTRAP_IP, config.BOOTSTRAP_PORT, config.TOTAL_NODES, False)
        print("end of init phase")
        n = node_wrapper.node
        time.sleep(secs)
        print(f'starting time: {time.time()}')

        n.create_transaction(2, 6)
        n.create_transaction(4, 8)
        n.create_transaction(0, 9)
        n.create_transaction(2, 10)
        n.create_transaction(1, 8)
        n.create_transaction(2, 9)
        n.create_transaction(2, 7)
        n.create_transaction(4, 5)
        n.create_transaction(4, 2)
        n.create_transaction(0, 7)
        n.create_transaction(4, 8)
        n.create_transaction(1, 3)
        n.create_transaction(1, 7)
        n.create_transaction(1, 9)
        n.create_transaction(1, 3)
        n.create_transaction(4, 8)
        n.create_transaction(1, 6)
        n.create_transaction(2, 4)
        n.create_transaction(0, 6)
        n.create_transaction(0, 5)
        n.create_transaction(0, 4)
        n.create_transaction(2, 9)
        n.create_transaction(4, 9)
        n.create_transaction(0, 9)
        n.create_transaction(1, 6)
        n.create_transaction(4, 2)
        n.create_transaction(2, 8)
        n.create_transaction(2, 10)
        n.create_transaction(4, 2)
        n.create_transaction(4, 3)
        n.create_transaction(2, 1)
        n.create_transaction(4, 8)
        n.create_transaction(2, 2)
        n.create_transaction(0, 5)
        n.create_transaction(0, 5)
        n.create_transaction(2, 7)
        n.create_transaction(4, 3)
        n.create_transaction(1, 3)
        n.create_transaction(0, 3)
        n.create_transaction(2, 1)
        n.create_transaction(2, 10)
        n.create_transaction(2, 6)
        n.create_transaction(0, 9)
        n.create_transaction(0, 10)
        n.create_transaction(2, 1)
        n.create_transaction(2, 9)
        n.create_transaction(2, 2)
        n.create_transaction(2, 10)
        n.create_transaction(0, 4)
        n.create_transaction(4, 5)
        n.create_transaction(0, 5)
        n.create_transaction(0, 2)
        n.create_transaction(0, 4)
        n.create_transaction(1, 9)
        n.create_transaction(0, 4)
        n.create_transaction(1, 6)
        n.create_transaction(4, 3)
        n.create_transaction(1, 3)
        n.create_transaction(2, 8)
        n.create_transaction(4, 8)
        n.create_transaction(2, 2)
        n.create_transaction(1, 4)
        n.create_transaction(4, 2)
        n.create_transaction(4, 2)
        n.create_transaction(2, 8)
        n.create_transaction(2, 7)
        n.create_transaction(0, 9)
        n.create_transaction(0, 3)
        n.create_transaction(4, 8)
        n.create_transaction(0, 5)
        n.create_transaction(2, 1)
        n.create_transaction(2, 5)
        n.create_transaction(1, 3)
        n.create_transaction(0, 7)
        n.create_transaction(2, 8)
        n.create_transaction(0, 6)
        n.create_transaction(4, 7)
        n.create_transaction(1, 8)
        n.create_transaction(4, 6)
        n.create_transaction(0, 5)
        n.create_transaction(4, 1)
        n.create_transaction(2, 2)
        n.create_transaction(0, 10)
        n.create_transaction(2, 9)
        n.create_transaction(0, 3)
        n.create_transaction(0, 4)
        n.create_transaction(0, 1)
        n.create_transaction(4, 6)
        n.create_transaction(2, 10)
        n.create_transaction(4, 6)
        n.create_transaction(2, 3)
        n.create_transaction(1, 7)
        n.create_transaction(2, 5)
        n.create_transaction(4, 6)
        n.create_transaction(2, 9)
        n.create_transaction(0, 2)
        n.create_transaction(1, 8)
        n.create_transaction(1, 7)
        n.create_transaction(4, 1)
        n.create_transaction(1, 2)
        test_func(n)

    elif role == "node5":
        node_wrapper = node_network_wrapper(config.NODE_IP, config.NODE_PORT+3, config.BOOTSTRAP_IP, config.BOOTSTRAP_PORT, config.TOTAL_NODES, False)
        print("end of init phase")
        n = node_wrapper.node
        time.sleep(secs)
        print(f'starting time: {time.time()}')

        n.create_transaction(3, 5)
        n.create_transaction(0, 4)
        n.create_transaction(1, 1)
        n.create_transaction(0, 5)
        n.create_transaction(2, 2)
        n.create_transaction(1, 9)
        n.create_transaction(0, 1)
        n.create_transaction(3, 5)
        n.create_transaction(3, 4)
        n.create_transaction(0, 1047)
        n.create_transaction(0, 3)
        n.create_transaction(1, 6)
        n.create_transaction(0, 9)
        n.create_transaction(3, 9)
        n.create_transaction(1, 8)
        n.create_transaction(0, 1)
        n.create_transaction(2, 3)
        n.create_transaction(0, 4)
        n.create_transaction(0, 7)
        n.create_transaction(0, 8)
        n.create_transaction(2, 4)
        n.create_transaction(2, 1065)
        n.create_transaction(3, 8)
        n.create_transaction(3, 2)
        n.create_transaction(3, 6)
        n.create_transaction(2, 8)
        n.create_transaction(1, 5)
        n.create_transaction(1, 2)
        n.create_transaction(1, 1)
        n.create_transaction(2, 1045)
        n.create_transaction(2, 4)
        n.create_transaction(1, 6)
        n.create_transaction(2, 8)
        n.create_transaction(1, 4)
        n.create_transaction(0, 4)
        n.create_transaction(2, 1)
        n.create_transaction(1, 6)
        n.create_transaction(3, 9)
        n.create_transaction(2, 5)
        n.create_transaction(2, 1)
        n.create_transaction(0, 4)
        n.create_transaction(3, 9)
        n.create_transaction(3, 6)
        n.create_transaction(1, 9)
        n.create_transaction(1, 7)
        n.create_transaction(0, 6)
        n.create_transaction(2, 5)
        n.create_transaction(0, 9)
        n.create_transaction(0, 8)
        n.create_transaction(2, 1)
        n.create_transaction(2, 7)
        n.create_transaction(0, 2)
        n.create_transaction(2, 4)
        n.create_transaction(3, 6)
        n.create_transaction(1, 2)
        n.create_transaction(3, 3)
        n.create_transaction(0, 8)
        n.create_transaction(0, 9)
        n.create_transaction(1, 1)
        n.create_transaction(0, 5)
        n.create_transaction(2, 7)
        n.create_transaction(0, 7)
        n.create_transaction(3, 8)
        n.create_transaction(3, 8)
        n.create_transaction(3, 1054)
        n.create_transaction(2, 9)
        n.create_transaction(2, 9)
        n.create_transaction(1, 6)
        n.create_transaction(0, 7)
        n.create_transaction(1, 6)
        n.create_transaction(0, 9)
        n.create_transaction(2, 1)
        n.create_transaction(3, 1)
        n.create_transaction(1, 9)
        n.create_transaction(3, 9)
        n.create_transaction(2, 3)
        n.create_transaction(2, 4)
        n.create_transaction(0, 5)
        n.create_transaction(2, 6)
        n.create_transaction(2, 6)
        n.create_transaction(3, 5)
        n.create_transaction(1, 1)
        n.create_transaction(1, 3)
        n.create_transaction(2, 1)
        n.create_transaction(3, 9)
        n.create_transaction(0, 197)
        n.create_transaction(0, 6)
        n.create_transaction(0, 5)
        n.create_transaction(0, 3)
        n.create_transaction(1, 2)
        n.create_transaction(2, 4)
        n.create_transaction(0, 8)
        n.create_transaction(3, 7)
        n.create_transaction(1, 3)
        n.create_transaction(3, 1000)
        n.create_transaction(0, 6)
        n.create_transaction(2, 8)
        n.create_transaction(3, 6)
        n.create_transaction(1, 9)
        n.create_transaction(3, 6)
        test_func(n)