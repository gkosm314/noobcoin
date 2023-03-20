from flask import Flask
from flask_restful import reqparse, abort, Api, Resource
import threading

# maybe put them also in bootstrap_api_server?
app = Flask(__name__)  
api = Api(app)

class node_api_server():
    def __init__(self, ip_arg, port_arg, parent_class_arg):
        self.ip = ip_arg
        self.port = port_arg
        self.parent_class = parent_class_arg
        api.add_resource(self.net_info_endpoint, '/net-info', resource_class_kwargs={'network_wrapper_class_arg': self.parent_class})

    def run(self):
        t = threading.Thread(target=lambda: app.run(host=self.ip, port=self.port, debug=True, use_reloader=False))
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
            args = self.parser.parse_args()
            public_keys_table = args['public_keys_table']
            ips_table = args['ips_table']
            genesis_block = args['genesis_block']
            print(f"[POST registr handler] received req with params:\n\tpublic_keys_table: {public_keys_table}\n\tips_table: {ips_table}\n\tgenesis_block: {genesis_block}")                
            
            self.node_wrapper.save_net_info(public_keys_table, ips_table, genesis_block)

            return {"status": "OK"}, 201


class bootstrap_api_server():
    def __init__(self, ip_arg, port_arg, parent_class_arg):
        self.ip = ip_arg
        self.port = port_arg
        self.parent_class = parent_class_arg
        
        api.add_resource(self.register_endpoint, '/register', resource_class_kwargs={'network_wrapper_class_arg': self.parent_class})


    def run(self):
        t = threading.Thread(target=lambda: app.run(host=self.ip, port=self.port, debug=True, use_reloader=False))
        t.start()

    class register_endpoint(Resource):
        def __init__(self, network_wrapper_class_arg):
            self.bootstrap_wrapper = network_wrapper_class_arg

            self.parser = reqparse.RequestParser()
            self.parser.add_argument('my_public_key')
            self.parser.add_argument('my_ip')
            self.parser.add_argument('my_port')


        # each node will post to this endpoint for registration
        def post(self):
            args = self.parser.parse_args()
            node_ip = args['my_ip']
            node_port = args['my_port']
            node_pub_key = args['my_public_key']
            print(f"[POST registr handler] received req with params:\n\tip: {node_ip}\n\tport: {node_port}\n\tpublic key: {node_pub_key}")                
            
            res_msg = self.bootstrap_wrapper.register_node(node_ip, node_port, node_pub_key)
            res_code = 201 if res_msg["added"] == True else 500

            return res_msg, res_code
