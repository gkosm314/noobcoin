import block
import transaction
import state

import logging

class Blockchain:

	def __init__(self, genesis_block: block, public_key_values):
		'''
		Constructs a blockchain.
		Since an empty blockchain is meaningless, we include the genesis block in the constructor.
		This object keeps the list of validated blocks and the UTXOs at the end of the 
		'''

		#list of public keys
		self.public_key_list = public_key_values

        #list of validated blocks
        #type: list of 'block' objects		
		self.chain = [genesis_block]

		#Create an empty utxo state for the public addresses that will be involved in this blockchain
		self.state = state.State(self.public_key_list, genesis_block)

		#Empty set that will include all transaction_id of every transaction in the blockchain
		self.transactions_included = set()

	def __len__(self):
		return len(self.chain)

	def attach_block(self, new_block: block):
		'''
		Assumption: the new_block is already validated.
		'''
		logging.info("attach block starts")
		#Execute each transaction inside the block and add its id to the set of transactions included in the blockchain
		#We do not validate because we assume that the TX is already validated by whoever added it to the block
		for tx in new_block.transactions:
			self.state.execute_transcation(tx)
			self.transactions_included.add(tx.transaction_id)

		#Append new block to the list of validated blocks and update blockchain's available UTXOs
		self.chain.append(new_block)
		logging.info("attach block end")

	def hashes_of_blocks(self):
		return [b.current_hash for b in self.chain]

	def attach_chain(self, list_of_blocks, hash_of_last_remaining_block):

		index_of_last_remaining_block = 0
		while self.chain[index_of_last_remaining_block].current_hash != hash_of_last_remaining_block:
			index_of_last_remaining_block += 1

		#List of transactions that were undone (some of them will be redone by the new chain)
		tx_of_removed_chain = []
		
		#Get the transactions of the chain you will remove
		for b in self.chain[(index_of_last_remaining_block+1):]:
			for tx in b.transactions:
				tx_of_removed_chain.append(tx)

		#From end to start, undo the transaction and remove it from transactions_included set
		for tx in reversed(tx_of_removed_chain):
				#self.state.undo_transaction(tx)
				self.transactions_included.remove(tx.transaction_id)

		#For the new chain, execute the transaction and add it to transaction_included set
		for b in list_of_blocks:
			for tx in b.transactions:
				#self.state.execute_transcation(tx)
				self.transactions_included.add(tx.transaction_id)

		#Keep the remaining part of the list and concat the list of the new blocks
		self.chain = self.chain[0:(index_of_last_remaining_block+1)] + list_of_blocks

		#Reconstruct blockchain state - TODO: replace with undo and redo
		self.state = state.State(self.public_key_list, self.chain[0])
		for b in self.chain:
			if b.index == 0:
				continue
			else:
				for tx in b.transactions:
					self.state.execute_transcation(tx)

		return tx_of_removed_chain
