import block
import transaction

class Blockchain:

	def __init__(self, genesis_block: block, public_key_values):
		'''
		Constructs a blockchain.
		Since an empty blockchain is meaningless, we include the genesis block in the constructor.
		This object keeps the list of validated blocks and the UTXOs at the end of the 
		'''

        #list of validated blocks
        #type: list of 'block' objects		
		self.chain = [genesis_block]

		#self.utxo 						- dict such that utxo[public] is a dict of utxos
		#self.utxo 						- dict of dicts of utxos
		#self.utxo[public_key]			- dict of utxos
		#self.utxo[public_key][utxo_id]	- TransactionOutput object	
		
		self.utxo = dict()
		for public_key in public_key_values:
			self.utxo[public_key] = dict()

		#self.wallet_sum - dict such that wallet_sum[public_key] = sum of TransactionOutput.value inside self.utxo[public_key]
		self.wallet_sum = dict()
		for public_key in public_key_values:
			self.wallet_sum[public_key] = 0	

		#Add initial UTXO of bootstrap node
		initial_tx = genesis_block.transactions[0]
		initial_utxo = transaction.TransactionOutput(initial_tx.transaction_id, 0, initial_tx.receiver_address, initial_tx.amount)
		self.utxo[initial_tx.receiver_address][initial_utxo.output_id] = initial_utxo


	def __len__(self):
		return len(self.chain)

	def add_block(self, new_block: block, new_block_utxo):
		'''
		Assumption: the new_block is already validated.
		'''
		
		#Append new block to the list of validated blocks and update blockchain's available UTXOs
		self.chain.append(new_block)
		self.utxo = new_block_utxo

