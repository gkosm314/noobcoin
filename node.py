import wallet
import block
import blockchain
import transaction
import rsa
import state
from copy import deepcopy
import config
import jsonpickle
import requests
import threading
from multiprocessing.pool import ThreadPool as Pool
import time
import logging

class bootstrap_node:

	def __init__(self, number_of_nodes_arg, bootstrap_ip_arg, bootstrap_port_arg):
		logging.info("initializing bootstrap")
		self.wallet = wallet.Wallet()
		self.number_of_nodes = number_of_nodes_arg
		self.public_key_table = {0: self.wallet.public_key}
		self.network_info_table = {self.wallet.public_key: (bootstrap_ip_arg, bootstrap_port_arg)}
		self.max_id = 0
		self.create_genesis_block()
		
	def create_genesis_block(self):
		''' Construct a block and manually configure it to be the genesis block '''

		self.g = block.Block(0,b'1')
		self.g.nonce = 0
		
		#Create the initial transaction that loads the bootstrap with coins
		initial_transaction_args = {
			"sender_address": 0,
			"receiver_address": self.wallet.public_key,
			"amount": 100*self.number_of_nodes,
			"transaction_inputs": []
		}
		initial_tx = transaction.Transaction(initial_transaction_args)

		#Attention: initial_tx will NOT have TransactionInputs!
		#Hash and Sign the initial transaction
		initial_tx.hash()
		initial_tx.sign(self.wallet.private_key)
		
		#Add transaction to the genesis block
		#add_transaction method assumes initial_tx is already validated so there is no problem
		self.g.add_transaction(initial_tx)

		#Caclulate hash of genesis block
		self.g.msg_to_hash = str((self.g.index, self.g.timestamp, self.g.transactions, self.g.previous_hash, self.g.nonce))
		self.g.current_hash = rsa.compute_hash(self.g.msg_to_hash.encode(), 'SHA-1')

		return self.g
	
	def add_node(self, node_pub_key_arg, node_ip_arg, node_port_arg):
		if node_pub_key_arg in self.network_info_table:
			# if node already added don't add again
			return -1

		#Calculate new node id
		node_id = self.max_id + 1
		self.max_id += 1

		#Update tables with the new nodes information
		self.public_key_table[node_id] = node_pub_key_arg
		self.network_info_table[node_pub_key_arg] = (node_ip_arg, node_port_arg)


		logging.info(f"node {node_id} registered")
		return node_id

	def produce_node(self):
		return node(0, self.wallet.private_key, self.public_key_table, self.network_info_table, self.g)



class uninitialized_node:

	def __init__(self):
		self.wallet = wallet.Wallet()
		
	def set_node_id(self, node_id_arg):
		self.node_id = node_id_arg

	def set_public_key_table(self, public_key_table_arg):
		self.public_key_table = public_key_table_arg
		
	def set_network_info_table(self, network_info_table_arg):
		self.network_info_table = network_info_table_arg
	
	def set_genesis_block(self, genesis_block_arg):
		self.genesis_block = genesis_block_arg

	def produce_node(self):
		return node(self.node_id, self.wallet.private_key, self.public_key_table, self.network_info_table, self.genesis_block)


class node:

	def __init__(self, node_id_arg, private_key_arg, public_key_list_arg, network_info_dict_arg, genesis_block_arg):

		#self.node_id - int that represents the node's id
		self.node_id = node_id_arg

		#self.public_key - list such that public_key[id] = public key of node with given id
		self.private_key = private_key_arg
		self.public_key = public_key_list_arg

		#self.network_info - dict such that network_info[public_key]=(ip,port)
		self.network_info = network_info_dict_arg

		#blockchain that contains the valid blocks
		self.current_blockchain = blockchain.Blockchain(genesis_block_arg, public_key_list_arg.values())
		
		#empty block that will be filled with the transactions we will receive
		self.current_block = block.Block(1,genesis_block_arg.current_hash)
		# self.current_block_available = True
		
		#state the corresponds to the state of the blockchain if the transactions inside the current_block were executed
		self.current_state = state.State(public_key_list_arg.values(), genesis_block_arg)

		#list of transactions that wait to be processed by a block
		self.transactions_buffer = []

		#set of ids of UTXOs that this node has already spent = used to create a transaction
		self.utxos_already_spent = set()

		#lock which prevents mining while adding transactions to the current block
		self.mine_lock_held = False

		#lock which prevents two transactions to be created simultaneously
		self.create_tx_lock_held = threading.Lock()
		
		self.utxos_returned_as_change = dict()

		self.test_count_cancelled_tx = 0

		# start a new thread for mining:
		t = threading.Thread(target=lambda: self.poll_for_mining())
		t.start()

	def poll_for_mining(self):
		#If the block reached full capacity
		while 1:
			if self.current_block.full() and not self.mine_lock_held:
				self.mine_current_block()
			time.sleep(1)

	def create_transaction(self, recipient_id_arg, amount_arg):
		#Waiting so that no more than one transaction can be created simultaneously
		self.create_tx_lock_held.acquire()

		my_public_key = self.public_key[self.node_id]

		#Select appropriate UTXOs to cover the amount by including UTXOs until you reach the needed amount
		selected_utxos = []
		amount_accumulated = 0
		required_amount_reached = False

		#The UTXOs that this sender/node has available
		available_utxos = list(self.current_state.utxo[my_public_key].items()) + list(self.utxos_returned_as_change.items())

		#Iterated the avaialble utxos from the smallest to the largest one, so that you use the minimal possible total transfer amount
		for x in sorted(available_utxos, key=lambda i: i[1].value):
			#Skip UTXOs that you already spent
			if x[0] in self.utxos_already_spent:
				continue

			selected_utxos.append(x[1])
			amount_accumulated += x[1].value
			if amount_accumulated >= amount_arg:
				required_amount_reached = True
				break

		#Check if we could reach the amount with the coins in our wallet
		if required_amount_reached:	

			#Convert UTXOs to TransactionInputs
			tx_input_list = [transaction.TransactionInput(i) for i in selected_utxos]
			#Remove UTXOs from available UTXOs and add UTXO id to the set of ids of spent UTXOs
			for tx_input_to_remove in tx_input_list:
				self.utxos_already_spent.add(tx_input_to_remove.previous_output_id)
				if tx_input_to_remove.previous_output_id in self.utxos_returned_as_change:
					del self.utxos_returned_as_change[tx_input_to_remove.previous_output_id]

			#Construct the transaction object
			args = {
				"sender_address": my_public_key,
				"receiver_address": self.public_key[recipient_id_arg],
				"amount": amount_arg,
				"transaction_inputs": tx_input_list,
			}
			tx = transaction.Transaction(args)
			#Compute the transaction's hash
			tx.hash()
			#Sign the transaction with the wallet's private key
			tx.sign(self.private_key)
						
			#Broadcast transaction
			self.broadcast_transaction(tx)

			#Receive my transaction to handle it
			self.receive_transaction(tx)

			#Add TransactionOutput to the local list of my_utxos, if you have change returned to you
			if amount_accumulated > amount_arg:
				change_for_sender = amount_accumulated - amount_arg
				utxo_returned_back = transaction.TransactionOutput(tx.transaction_id,1,tx.sender_address,change_for_sender)
				self.utxos_returned_as_change[utxo_returned_back.output_id] = utxo_returned_back #dict: uxto id -> TransactionOutput object
		else:
			logging.info("Your wallet does not have enough coins for this transcaction to be performed.")
			self.test_count_cancelled_tx += 1 
			self.create_tx_lock_held.release()
			return False

		self.create_tx_lock_held.release()
		return True
		
	def view_transactions(self):
		'''Prints the transactions that are included in the last block.'''

		s = str(self.current_blockchain.chain[-1])
		print(f"\n NODE #{self.node_id} - " + s)
		return s

	def add_transaction_to_current_block(self, tx: transaction):
		'''
		Adds a transaction to the current block.
		If the current block becomes full by this transaction, the mining process is triggered.
		'''
		self.mine_lock_held = True
		#If the block is valid, execute it on the current block's state (not on the global blockchain state)
		#Otherwise throw it away
		if self.current_state.validate_transaction(tx):
			#Execute transaction on the current state and add it to the current block
			self.current_state.execute_transcation(tx)
			self.current_block.add_transaction(tx)
		self.mine_lock_held = False

	def receive_transaction(self, tx: transaction):
		''' This method is called by the network_wrapper when a transaction is received.'''
		logging.info(f"receive tx {tx.transaction_id}")
		#If the current_block still accepts more TXs, then work with it
		# if self.current_block_available:
		if not self.current_block.full():
			self.add_transaction_to_current_block(tx)
		else:
			#If the current_block is full, append the TX to a buffer so that a future block can grab it
			logging.info("yo")
			self.transactions_buffer.append(tx)

	def mine_current_block(self):
		logging.info("start mine_current_block")
		# #Flag current_block as unavailable
		# self.current_block_available = False

		#Mine this block
		t = threading.Thread(target=lambda: self.current_block.mine())
		t.start()
		t.join()
		
		block_got_attached_flag = False
		#If the block got mined, attempt to attach the block to the blockchain (like you would if you had received it from another node)
		if self.current_block.is_mined:
			#Set flag to True if you managed to attach the block
			logging.info("block mined - attempt to attach it")
			block_got_attached_flag = self.receive_block(self.current_block, False)
			
		#If you managed to attach the block, broadcast it to everyone, otherwise refill the buffer with the pending transaction
		if block_got_attached_flag:
			#If you are successful, broadcast the mined block to the other nodes so that they can attempt to attach it too
			self.broadcast_block(self.current_block)
		else:
			#TODO: put the TXs of the mined block that were not included in the blockchain
			#after the conflict resolution back to the start of the transaction, so that they can be processed by a future block
			transactions_to_reprocess = []
			for tx in self.current_block.transactions:
				if not (tx in self.current_blockchain.transactions_included):
					transactions_to_reprocess.append(tx)
			self.transactions_buffer = transactions_to_reprocess + self.transactions_buffer
		
		logging.info("start creation of new block")
		#Create a new empty current_block and a new updated state
		last_block = self.current_blockchain.chain[-1]
		self.current_block = block.Block(last_block.index + 1, last_block.current_hash)
		self.current_state = deepcopy(self.current_blockchain.state)
		logging.info("end creation of new block")

		logging.info("start consuming transaction buffer")
		#TODO: discuss this...
		logging.info(self.transactions_buffer)
		while self.transactions_buffer:
			tx = self.transactions_buffer.pop()
			self.add_transaction_to_current_block(tx)
		# print("stop consuming transaction buffer")
		logging.info(self.transactions_buffer)

		# #Flag current_block as unavailable
		# self.current_block_available = True

		logging.info("end mine_current_block")

	def broadcast_transaction(self, tx: transaction):
		'''Broadcasts a block to every node'''

		#Grab my network info
		my_network_info = self.network_info[self.public_key[self.node_id]]

		headers = {"Content-Type": "application/json; charset=utf-8"}
		payload_dict = {
			"tx_obj": tx, 
		}
		payload_json = jsonpickle.encode(payload_dict, keys=True)
		
		def unicast(ip_arg, port_arg, payload_json_arg):
			req = requests.post(f"http://{ip_arg}:{port_arg}/post_transaction", headers=headers, data=payload_json_arg)

		senders = self.network_info.values()
		pool = Pool(len(senders)-1)

		for (ip, port) in senders:
			if (ip, port) == my_network_info:
				continue			
			pool.apply_async(unicast, (ip, port, payload_json,))

		pool.close()
		pool.join()

	def wallet_balance(self, node_id_arg):
		'''Returns the balance of a specific public address.'''
		return self.current_blockchain.state.wallet_sum[self.public_key[node_id_arg]]

	def broadcast_block(self, b: block):
		'''Broadcasts a block to every node'''

		#Grab my network info
		my_network_info = self.network_info[self.public_key[self.node_id]]

		headers = {"Content-Type": "application/json; charset=utf-8"}
		payload_dict = {"block_obj": b}
		payload_json = jsonpickle.encode(payload_dict, keys=True)

		def unicast(ip_arg, port_arg, payload_json_arg):
			req = requests.post(f"http://{ip_arg}:{port_arg}/post_block", headers=headers, data=payload_json_arg)

		senders = self.network_info.values()
		pool = Pool(len(senders)-1)

		for (ip, port) in senders:
			if (ip, port) == my_network_info:
				continue
			pool.apply_async(unicast, (ip, port, payload_json,))
		pool.close()
		pool.join()
	
	def valid_hash_of_block(self, b: block):
		'''Check that the current_hash of the block_to_validate is actually its hash by recalculating it'''	
		
		#Note: this one-liner is also used at mine() in block.py. In case it is changed, change it there too!
		hash_begins_with_d_zeros_flag = block.starts_with_difficulty_zeros(b.current_hash, config.difficulty)

		#If this raises and error after deserialization to a different node, change m to self.msg_to_hash
		m = str((b.index, b.timestamp, b.transaction_hashes, b.previous_hash, b.nonce))
		logging.info(b.msg_to_hash)
		logging.info(m)
		if (rsa.compute_hash(m.encode(), 'SHA-1') == b.current_hash) and hash_begins_with_d_zeros_flag:
			return True
		else:
			return False

	def validate_block(self, block_to_validate: block):
		'''
		This function is called after a block was received.
		It checks that current_hash actually is the hash of the block and
		that the previous_hash of the block equals the current_hash of the last block of the blockchain.
		Note: this function should not be called for the genesis block
		'''
		logging.info("validate block starts")
		#Check that the current_hash of the block_to_validate is actually its hash by recalculating the hash
		if not self.valid_hash_of_block(block_to_validate):
			raise Exception("We received a block whose current_hash is different than the one we computed for it.")

		#Check that the previous_hash of the block_to_validate is the current hash of the last block in the chain
		try:
			if self.current_blockchain.chain[-1].current_hash != block_to_validate.previous_hash:
				logging.info(len(self.current_blockchain.chain))
				logging.info(self.current_blockchain.chain[-1].current_hash)
				logging.info(block_to_validate.previous_hash)
				logging.info("validate block returns False")
				return False
		except:
			raise "This function should not be called for the genesis block."

		#If both checks are succesful, then the block is valid
		logging.info("validate block returns True")
		return True

	def validate_chain(self, blockchain_to_validate: blockchain):
		'''
		Iterate over every block except the genesis block and ensure that it is valid.
		The validation check is the same as the one that we use in validate_block(), but we do not reuse the function.
		'''
	
		#Iterate over every block except the genesis block
		#If you find a non-valid block then the whole blockchain is invalid
		for block_index in range(1,len(blockchain_to_validate)):
			#Compare the current_hash of the previous block to the current_hash of this block
			if blockchain_to_validate.chain[block_index-1].current_hash != blockchain_to_validate.chain[block_index].previous_hash:
				return False
			if not self.valid_hash_of_block(blockchain_to_validate.chain[block_index]):
				return False

		#Otherwise the blockchain is valid
		return True

	def receive_block(self, b: block, block_received_from_network_flag):
		'''
		This method is called by the network_wrapper when a block (from an external node) is received.
		Returns True if we managed to append the 
		'''

		#Check that the block is valid:
		#	- correctly calculated hash (!Note: in this case an Exception will be thrown)
		#	- previous_hash equals current_hash of the last block already in the blockchain (in this case return False)

		self.current_blockchain.change_blockchain.acquire()
		logging.info(f"receive block starts - received from network {block_received_from_network_flag}")
		if self.validate_block(b):
			#If the block is valid for the blockchain, attach it and return True
			self.current_blockchain.attach_block(b)
			self.current_block.is_outdated = True #since I attached a block, the current_block is now outdated, even if it is the one we attached
			self.current_blockchain.change_blockchain.release()
			logging.info("receive block ends with attachment")
			return True
		else:
			#Otherwise, ask the other nodes to help you continue and then return False as you didn't manage to attach the block
			if block_received_from_network_flag:
				self.resolve_conflict()
				logging.info("receive block ends with resolution")
			self.current_blockchain.change_blockchain.release()
			return False

	def resolve_conflict(self):
		#DO NOT FORGET TO UPDATE self.current_blockchain.transactions_included

		#Broadcast request for blockchain length
		headers = {"Content-Type": "application/json; charset=utf-8"}
		senders = self.public_key.items()
		all_blockchain_lengths = [-1 for _ in senders] #save all the received values for reduction (max)

		def unicast(tid, pub_addr_of_node_arg):
			#Grab network info of external node
			(ip, port) = self.network_info[pub_addr_of_node]

			#Send request for blockchain length and extract the length from the response
			req = requests.post(f"http://{ip}:{port}/request_blockchain_length", headers=headers)
			
			payload_dict = jsonpickle.decode(req.json(), keys=True)
			all_blockchain_lengths[tid] = payload_dict["length"]
			# print("received length: ", all_blockchain_lengths)

		pool = Pool(len(senders)-1)

		#Iterate over node ids to send request and choose who is going to solve your conflict
		for (id_of_node,pub_addr_of_node) in senders:
			#Do not ask yourself for conflict resolution
			if id_of_node == self.node_id:
				continue
			pool.apply_async(unicast, (id_of_node, pub_addr_of_node,))
		pool.close()
		pool.join()

		#Initialize variable for the maximum length sent so far by other nodes
		longest_blockchain_node = self.node_id
		longest_blockchain_length = len(self.current_blockchain)
		
		#Compute the maximum length and the node who posseses that
		for id_of_node, length_of_blockchain in enumerate(all_blockchain_lengths):
			#Compare the length you received to find out which node to ask for its blockchain
			if length_of_blockchain > longest_blockchain_length:
				longest_blockchain_node = id_of_node
				longest_blockchain_length = length_of_blockchain
			elif (length_of_blockchain == longest_blockchain_length) and (id_of_node < longest_blockchain_node):
				longest_blockchain_node = id_of_node
				longest_blockchain_length = length_of_blockchain
		
		if longest_blockchain_node == self.node_id:
			return True
		
		#Grab the hashes of the blocks in the blockchain and construct the payload
		hashes_of_blockchain = self.current_blockchain.hashes_of_blocks()
		hashes_of_blockchain_payload_dict = {"hashes_list": hashes_of_blockchain}
		# print(hashes_of_blockchain_payload_dict)
		hashes_of_blockchain_payload_json = jsonpickle.encode(hashes_of_blockchain_payload_dict, keys=True)

		#Send request to the node with the largest 
		longest_bchain_node_pubkey = self.public_key[longest_blockchain_node] # find the ip, port of...
		ip, port = self.network_info[longest_bchain_node_pubkey]              # ...the longest blockchain node
		req = requests.post(f"http://{ip}:{port}/request_blockchain_diff", headers=headers, data=hashes_of_blockchain_payload_json)
		# print("\n\n\n\n handling stuff")
		payload_dict = jsonpickle.decode(req.json(), keys=True)

		#TODO: deserialize response to this request and extract
		#	- current_block of the last block that survives
		#	- list of Block objects that will be added to the Blockchain to solve the conflict

		list_of_new_blocks = payload_dict["list_of_blocks"]
		hash_of_parent_block = payload_dict["parent_hash"]
		expected_length_after_attach = payload_dict["length_after_attach"]

		#Attach the chain to the blockchain, if it is still the longest chain
		if expected_length_after_attach > len(self.current_blockchain):
			transcations_of_removed_chain = self.current_blockchain.attach_chain(list_of_new_blocks, hash_of_parent_block)	
			#If the transaction was not included in the final blockchain (= re-entered by the new chain),then it needs to be processed again!
			for tx in transcations_of_removed_chain:
				if not (tx in self.current_blockchain.transactions_included):
					self.transactions_buffer.append(tx)