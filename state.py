import rsa
import block
import transaction

class State(object):

	def __init__(self, public_key_values, genesis_block_arg: block):
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

		#Initialize state by adding the UTXO of the initial transaction
		initial_tx = genesis_block_arg.transactions[0]

		#Manually construct UTXO of initial transaction since generate_outputs requires TransactionInputs 
		initial_utxo = transaction.TransactionOutput(initial_tx.transaction_id, 0, initial_tx.receiver_address, initial_tx.amount)
		
		#Add the UTXO to the recipient's (=bootstrap) UTXOs and update its wallet
		self.utxo[initial_utxo.recipient_address][initial_utxo.output_id] = initial_utxo

	def add_utxo(self, utxo_arg):
		#Add UTXO and update recipient's wallet amount
		self.utxo[utxo_arg.recipient_address][utxo_arg.output_id] = utxo_arg
		self.wallet_sum[utxo_arg.recipient_address] += utxo_arg.value

	def remove_utxo(self, transaction_input_arg, tx_sender_address_arg):
		'''Takes a TransactionInput and the sender's address and removes the respective UXTO'''
		del self.utxo[tx_sender_address_arg][transaction_input_arg.previous_output_id]
		self.wallet_sum[tx_sender_address_arg] -= transaction_input_arg.value

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

		Attention: UTXOs are checked against state = the state of the current_block that we fill with new TXs
		'''

		#Verify the transaction's signature
		if not self.verify_signature(tx):
			return False

		#Calculate the sum of the given transaction inputs and check that each one of them is unspent
		tx_inputs_sum = 0
		for i in tx.transaction_inputs:
			#Iterate over the inputs of the Transaction and check that each of them is currently a UTXO
			if not i.previous_output_id in self.utxo[tx.sender_address]:
				return False
			else:
				tx_inputs_sum += i.value

		#Check that the sum of the inputs used for this transaction is enough to cover the spent amount
		if tx_inputs_sum < tx.amount:
			return False
		else:
			return True

	def execute_transcation(self, tx: transaction):
		'''
		Execute transaction by changing the state.
		Assumes that the transaction is already validated.
		'''

		#Remove the transaction inputs from UTXOs and substract their amount from the sender's balance
		for i in tx.transaction_inputs:
			self.remove_utxo(i, tx.sender_address)

		#Generate TransactionOutputs and add them to the current state's UTXOs
		tx.generate_outputs()
		for new_utxo in tx.transaction_outputs:
			self.add_utxo(new_utxo)
			
		return True