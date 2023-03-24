from flask import Flask
from flask_restful import reqparse, abort, Api, Resource, request
import threading
import json, jsonpickle
import sys

cli = sys.modules['flask.cli']
cli.show_server_banner = lambda *x: None
# maybe put them also in bootstrap_api_server?
app = Flask(__name__)  
api = Api(app)

class node_api_server():
    def __init__(self, ip_arg, port_arg, parent_class_arg):
        self.ip = ip_arg
        self.port = port_arg
        self.parent_class = parent_class_arg
        
        api.add_resource(self.register_endpoint, '/register', 
            resource_class_kwargs={'network_wrapper_class_arg': self.parent_class})

        api.add_resource(self.net_info_endpoint, '/post_net_info', 
            resource_class_kwargs={'network_wrapper_class_arg': self.parent_class})
        
        api.add_resource(self.transaction_endpoint, '/post_transaction', 
            resource_class_kwargs={'network_wrapper_class_arg': self.parent_class})

        api.add_resource(self.block_endpoint, '/post_block', 
            resource_class_kwargs={'network_wrapper_class_arg': self.parent_class})    
        
        api.add_resource(self.request_blockchain_length_endpoint, '/request_blockchain_length', 
            resource_class_kwargs={'network_wrapper_class_arg': self.parent_class})
        
        api.add_resource(self.request_blockchain_diff_endpoint, '/request_blockchain_diff', 
            resource_class_kwargs={'network_wrapper_class_arg': self.parent_class})
    
    def run(self):
        t = threading.Thread(target=lambda: app.run(host=self.ip, port=self.port)) #debug=True, use_reloader=False
        t.start()

    class net_info_endpoint(Resource):
        def __init__(self, network_wrapper_class_arg):
            self.node_wrapper = network_wrapper_class_arg

            self.parser = reqparse.RequestParser()
            self.parser.add_argument('public_keys_table')
            self.parser.add_argument('ips_table')
            self.parser.add_argument('genesis_block')

        # bootstrap will post to this endpoint to give the node net-info
        def post(self):
            payload_json = request.get_data()
            payload_dict = jsonpickle.decode(payload_json, keys=True)

            public_keys_table = payload_dict['public_keys_table']
            ips_table = payload_dict['ips_table']
            genesis_block = payload_dict['genesis_block']
            # print(f"[POST net-info handler] received req with params:\n\tpublic_keys_table: {public_keys_table}\n\tips_table: {ips_table}\n\tgenesis_block: {genesis_block}")                
            
            self.node_wrapper.save_net_info(public_keys_table, ips_table, genesis_block)

            return {"status": "OK"}, 201

    class transaction_endpoint(Resource):
        def __init__(self, network_wrapper_class_arg):
            self.node_wrapper = network_wrapper_class_arg

        def post(self):
            payload_json = request.get_data()
            payload_dict = jsonpickle.decode(payload_json, keys=True)

            tx = payload_dict['tx_obj']

            # print(f"[POST tx handler] received req with params:\n\ntx_obj: {tx}")                
            
            self.node_wrapper.handle_incoming_tx(tx)

            return {"status": "OK"}, 201
  
    class block_endpoint(Resource):
            def __init__(self, network_wrapper_class_arg):
                self.node_wrapper = network_wrapper_class_arg

            def post(self):
                payload_json = request.get_data()
                payload_dict = jsonpickle.decode(payload_json, keys=True)

                b = payload_dict['block_obj']

                # print(f"[POST block handler] received req with params:\n\ntx_obj: {tx}")                
                
                self.node_wrapper.handle_incoming_block(b)

                return {"status": "OK"}, 201

    class request_blockchain_length_endpoint(Resource):
        def __init__(self, network_wrapper_class_arg):
            self.node_wrapper = network_wrapper_class_arg

        # node which performs resolution hits this endpoint to get the nodes' blockchain length
        def post(self):
            # print(f"[POST request blockchain length handler] received req")                
            
            length = self.node_wrapper.get_blockchain_length()
            # print("\n\n\n\n\n\n\n\nLENGTH\n\n\n\n\n\n\n\n")
            payload_dict = {"length": length}
            payload_json = jsonpickle.encode(payload_dict, keys=True)
            return payload_json, 201

    class request_blockchain_diff_endpoint(Resource):
        def __init__(self, network_wrapper_class_arg):
            self.node_wrapper = network_wrapper_class_arg

        # node which performs resolution hits this endpoint to get the difference
        # in blocks from the node with the longest blockchain
        def post(self):
            # print(f"[POST request blockchain diff handler] received req")                
            
            incoming_payload_json = request.get_data()
            incoming_payload_dict = jsonpickle.decode(incoming_payload_json, keys=True)
            # print("\n\n\n\n\n\n", incoming_payload_dict)

            hashes_list = incoming_payload_dict["hashes_list"]
            blockchain_diff, parent_hash, length = self.node_wrapper.get_blockchain_diff(hashes_list)
            # print("\n\n\n\n\n", blockchain_diff)
            # print(parent_hash)

            outcoming_payload_dict = {
                "list_of_blocks": blockchain_diff,
                "parent_hash": parent_hash,
                "length_after_attach": length
            }
            outcoming_payload_json = jsonpickle.encode(outcoming_payload_dict, keys=True)

            return outcoming_payload_json, 201

    class register_endpoint(Resource):
        def __init__(self, network_wrapper_class_arg):
            self.bootstrap_wrapper = network_wrapper_class_arg

            self.parser = reqparse.RequestParser()
            self.parser.add_argument('my_public_key')
            self.parser.add_argument('my_ip')
            self.parser.add_argument('my_port')


        # each node will post to this endpoint for registration
        def post(self):
            payload_json = request.get_data()
            payload_dict = jsonpickle.decode(payload_json, keys=True)
            
            node_ip = payload_dict['my_ip']
            node_port = payload_dict['my_port']
            node_pub_key = payload_dict['my_public_key']
            # print(f"[POST registr handler] received req with params:\n\tip: {node_ip}\n\tport: {node_port}\n\tpublic key: {node_pub_key}")                
            
            res_msg = self.bootstrap_wrapper.register_node(node_ip, node_port, node_pub_key)
            res_code = 201 if res_msg["added"] == True else 500

            return res_msg, res_code
