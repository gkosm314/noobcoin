import requests
import json
import sys 
import time
import pickle

import node
from config import *
import rest_api
import wallet



class node_network_wrapper:
    
    def __init__(self, node_ip_arg, node_port_arg, bootstrap_ip_arg, bootstrap_port_arg):
        self.node = node.uninitialized_node()

        self.ip = node_ip_arg     # maybe move them to bootstrap_api_server
        self.port = node_port_arg # maybe move them to bootstrap_api_server
        self.bootstrap_ip = bootstrap_ip_arg     # maybe move them to bootstrap_api_server
        self.bootstrap_port = bootstrap_port_arg # maybe move them to bootstrap_api_server
        
        self.api_server = rest_api.node_api_server(self.ip, self.port, self)
        self.registration_completed = False # for the uninitialized node registration completes when mutates to node
        
        self.api_server.run() 
        time.sleep(3)
        self.register()

    def register(self):
        '''send public key to bootstrap'''

        headers = {"Content-Type": "application/json; charset=utf-8"}
        
        # serialize public key
        public_key = wallet.public_key2str(self.node.wallet.public_key)
        payload = {"my_public_key": public_key, "my_ip": self.ip, "my_port": self.port}
        req = requests.post(f"http://{self.bootstrap_ip}:{self.bootstrap_port}/register", headers=headers, data = json.dumps(payload))
        print("i just registered myself and received", req.json())
        

    def save_net_info(self, public_keys_table_arg, ips_table_arg, genesis_block_arg):
        
        # self.node.set_network_info_table(ips_table_arg)
        # self.node.set_public_key_table(public_keys_table_arg)
        # self.node.set_genesis_block(genesis_block_arg)

        # self.node = self.node.produce_node()
        self.registration_completed = True
        print("saving info...")


class boostrap_network_wrapper:
    
    def __init__(self, bootstrap_ip_arg, bootstrap_port_arg, total_nodes_arg):
        self.bootstrap_node = node.bootstrap_node(total_nodes_arg, bootstrap_ip_arg, bootstrap_port_arg)

        self.bootstrap_ip = bootstrap_ip_arg     # maybe move them to bootstrap_api_server
        self.bootstrap_port = bootstrap_port_arg # maybe move them to bootstrap_api_server
        self.api_server = rest_api.bootstrap_api_server(self.bootstrap_ip, self.bootstrap_port, self)
        self.nodes_cnt = 0
        self.registration_completed = False

        self.api_server.run()    
        
        while 1:
            if self.registration_completed: 
                print("All nodes registered")
                break
            time.sleep(1)

        self.bcast_initial_state()

    def register_node(self, node_ip, node_port, node_public_key): 
        if (self.nodes_cnt >= self.bootstrap_node.number_of_nodes):
            self.registration_completed = True
            return {"added": False, "assigned_id": -1}
        
        #de-serialize public key
        node_public_key = wallet.str2public_key(node_public_key)
        new_id = self.bootstrap_node.add_node(node_public_key, node_ip, node_port)
        
        if (new_id == -1): # node has been already added
            return {"added": False, "assigned_id": -1}

        self.nodes_cnt+=1

        return {"added": True, "assigned_id": new_id}


    def bcast_initial_state(self):
        '''Broadcast to all the nodes the network info table, public key table and genesis block'''
        
        print("broadcasting init state")
        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {
            'public_keys_table': wallet.public_keys_table2json(self.bootstrap_node.public_key_table), 
            'ips_table': wallet.network_info_table2json(self.bootstrap_node.network_info_table), 
            'genesis_block': self.bootstrap_node.g.toJSON()
        }
        
        for (ip, port) in self.bootstrap_node.network_info_table.values():
            req = requests.post(f"http://{ip}:{port}/net-info", headers=headers, data = json.dumps(payload))
            print(req.json())

    

if __name__=="__main__":
    role = sys.argv[1]

    if role == "bootstrap":
        bootstrap_wrapper = boostrap_network_wrapper(BOOTSTRAP_IP, BOOTSTRAP_PORT, TOTAL_NODES)
        print("end of init phase")

    elif role == "node1":
        node_wrapper = node_network_wrapper(NODE_IP, NODE_PORT, BOOTSTRAP_IP, BOOTSTRAP_PORT)
        print("end of init phase")

    elif role == "node2":
        node_wrapper = node_network_wrapper(NODE_IP, NODE_PORT+1, BOOTSTRAP_IP, BOOTSTRAP_PORT)
        print("end of init phase")




