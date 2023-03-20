import wallet
import block
import blockchain
import transaction
import rsa
from config import *

class bootstrap_node:

	def __init__(self, number_of_nodes_arg, bootstrap_ip_arg, bootstrap_port_arg):
		print("initializing bootstrap")
		self.wallet = wallet.Wallet()
		self.number_of_nodes = number_of_nodes_arg
		self.public_key_table = {}
		self.network_info_table = {} # TODO: I removed bootstrap data from the tables
		self.max_id = 0
		self.create_genesis_block()
		
	def create_genesis_block(self):
		''' Construct a block and manually configure it to be the genesis block '''

		self.g = block.Block(0,b"1")
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


		print(f"node {node_id} registered")
		return node_id

	
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

		self.current_blockchain = blockchain.Blockchain(genesis_block_arg, self.public_key.values())
		
		self.current_block = block.Block(1,genesis_block_arg.previous_hash)

	def create_transaction(self, recipient_id_arg, amount_arg):
		#Select appropriate UTXOs to cover the amount by including UTXOs until you reach the needed amount
		selected_utxos = []
		amount_accumulated = 0
		required_amount_reached = False

		#The UTXOs that this sender/node has available
		available_utxos = self.current_blockchain.utxo[self.public_key[self.node_id]].items()

		#Iterated the avaialble utxos from the smallest to the largest one, so that you use the minimal possible total transfer amount
		for i in sorted(available_utxos, key=lambda i: i[1].value):
			selected_utxos.append(i)
			amount_accumulated += i.value
			if amount_accumulated >= amount_arg:
				required_amount_reached = True
				break

		#Check if we could reach the amount with the coins in our wallet
		if required_amount_reached:	
			#Remove UTXOs from available UTXOs
			#TODO: discuss this
			for utxo_to_remove in selected_utxos:
				del self.current_blockchain.utxo[self.public_key[self.node_id]][utxo_to_remove.output_id]

			#Convert UTXOs to TransactionInputs
			tx_input_list = [TransactionInput(i) for i in selected_utxos]

			#Construct the transaction object
			args = {
				"sender_address": self.public_key[self.node_id],
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
		else:
			print("Your wallet does not have enough coins for this transcaction to be performed.")
			return False
		
	def view_transactions(self):
		'''Prints the transactions that are included in the last block.'''

		s = str(self.current_blockchain.chain[-1])
		print(f"\n NODE #{self.node_id} - " + s)
		return s

	def broadcast_transaction(self, tx: transaction):
		'''Broadcasts a block to every node'''

		headers = {"Content-Type": "application/json; charset=utf-8"}
		payload = tx.toJSON()
		for (ip, port) in self.bootstrap_node.network_info_table.values():
			req = requests.post(f"http://{ip}:{port}/receive_transaction", headers=headers, data = json.dumps(payload))

	def verify_signature(self, tx: transaction):
		'''
		Given a Transaction object, it recomputes the hash and verifies the signature.
		'''

		#If the signature cannot verified, an exception is thrown
		try:
			#tx.msg_to_hash is a string and rsa.verify() needs bytes, so we use .encode() method
			rsa.verify(tx.msg_to_hash.encode(), tx.signature, tx.sender_address)
		except:
			return False
		else:
			return True

	def validate_transaction(self, tx: transaction):
		'''
		Checks that a transaction is valid by:
			- verifying the signature
			- ensuring that the inputs of the transaction are actually UTXOs so that double spending is avoided
		'''

		#Verify the transaction's signature
		if not self.verify_signature(tx):
			return False

		#Calculate the sum of the given transaction inputs and check that each one of them is unspent
		tx_inputs_sum = 0
		for i in tx.transaction_inputs:
			#Iterate over the inputs of the Transaction and check that each of them is currently a UTXO
			#??? which state ???
			if not i.previous_output_id in self.current_blockchain.utxo[tx.sender_address]:
				return False
			else:
				tx_inputs_sum += i.value

		#Check that the sum of the inputs used for this transaction is enough to cover the spent amount
		if tx_inputs_sum < tx.amount:
			return False
		else:
			return True

	def execute_transcation(self, tx: transaction):
		''' '''

		#Validate the transaction
		if not validate_transaction(tx):
			return False

		#Remove the transaction inputs from current UTXOs and substract their amount from the sender's balance
		for i in tx.transaction_inputs:
			del self.current_blockchain.utxo[tx.sender_address][i.previous_output_id]
			self.current_blockchain.wallet_sum[tx.sender_address] -= i.value

		#Add transaction to the block and add them to the UTXO data structure
		self.current_block.add_transaction(tx)

		#Generate TransactionOutputs, add them to the current UTXOs and add their amount to the correct balances
		tx.generate_outputs()
		for new_utxo in tx.transaction_outputs:
			self.current_blockchain.utxo[new_utxo.recipient_address][new_utxo.output_id] = new_utxo
			self.current_blockchain.wallet_sum[new_utxo.recipient_address] += new_utxo.value #Note that each generated UTXO has a different recipient

		#If the block reached full capacity
		if self.current_block.full():
			#Mine this block
			self.current_block.mine()

			#Broadcast the mined block
			self.broadcast_block(self.current_block)
			
			#Create a new block for the upcoming transactions
			self.current_block = block.Block(self.current_block.current_index + 1, self.current_block.current_hash)
			#self.current_block_utxo = self.current_blockchain.utxo

		return True

	def wallet_balance(self, public_key_arg):
		'''Returns the balance of a specific public address.'''
		return self.current_blockchain.wallet_sum[public_key_arg]

	def broadcast_block(self, b: block):
		'''Broadcasts a block to every node'''

		headers = {"Content-Type": "application/json; charset=utf-8"}
		payload = b.toJSON()
		for (ip, port) in self.bootstrap_node.network_info_table.values():
			req = requests.post(f"http://{ip}:{port}/receive_block", headers=headers, data = json.dumps(payload))
	
	def valid_hash_of_block(self, b: block):
		'''Check that the current_hash of the block_to_validate is actually its hash by recalculating it'''	
		
		#Note: this one-liner is also used at mine() in block.py. In case it is changed, change it there too!
		hash_begins_with_d_zeros_flag = block.starts_with_difficulty_zeros(b.current_hash, difficulty)

		#If this raises and error after deserialization to a different node, change m to self.msg_to_hash
		m = str((b.index, b.timestamp, b.transactions, b.previous_hash, b.nonce))
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

		#Check that the current_hash of the block_to_validate is actually its hash by recalculating the hash
		if not self.valid_hash_of_block(block_to_validate):
			return False

		#Check that the previous_hash of the block_to_validate is the current hash of the last block in the chain
		try:
			if self.current_blockchain.chain[-1].current_hash != block_to_validate.previous_hash:
				return False
		except:
			raise "This function should not be called for the genesis block."

		#If both checks are succesful, then the block is valid
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

	def resolve_conflict(self):
		print("TODO: Implement resolve conflict...")