import rsa
import wallet

class Transaction:

	def __init__(self, args):

		#public key of sender
		self.sender_address = args["sender_address"]

		#public key of receiver
		self.receiver_address = args["receiver_address"]

		#amount transfered - not the sum of the TransactionInput objects
		if args["amount"] >= 0:
			self.amount = args["amount"]
		else:
			raise Exception("You cannot transfer a negative amount to a recipient.")

		#list of TransactionInput objects
		self.transaction_inputs = args["transaction_inputs"]

		#string of a tuple that contains what we want to hashed - string needs to be converted to bytes to be hashed
		self.msg_to_hash = str((self.sender_address, self.receiver_address, self.amount, self.transaction_inputs))

		#flags that indicate the current state of the Transaction
		self.is_hashed = False
		self.is_signed = False
		self.output_generated = False

	def __str__(self):
		'''
		Implements string method that is called when you attempt to print() the transaction.
		'''

		if self.is_hashed and self.is_signed:
			s = f'''
	------------------
	Transaction Id: {self.transaction_id.hex()}
	Amount: {self.amount}
	Sender: {self.sender_address}
	Receiver: {self.receiver_address}
	------------------
			'''
			return s

		else:
			return "Transaction is either unhashed or unsigned."		

	def hash(self):
		'''
		Computes the hash of the msg_to_hash variable, which we define in the __init__ constructor
		'''

		#Compute the hash and set the transaction_id and the relevant flag accordingly
		self.transaction_id = rsa.compute_hash(self.msg_to_hash.encode(), 'SHA-1')
		self.is_hashed = True

		return self.transaction_id

	def sign(self, private_key_arg):
		'''
		Assumption: the transaction is already hashed
		Takes the private key of the wallet as parameter
		'''

		#If the transaction is not already hashed, then we cannot sign it!
		if not self.is_hashed:
			raise Exception("Transaction is not hashed yet.")

		#Sign the hash using rsa.sign_hash(). Compute the signature and set the signature and the relevant flag accordingly
		#In order to verify the transaction, we use rsa.verify() with the message parameter set to msg_to_hash.encode()
		self.signature = rsa.sign_hash(self.transaction_id, private_key_arg, 'SHA-1')
		self.is_signed = True
		
		return self.signature

	def generate_outputs(self):
		'''
		Assumption: the transaction is already hashed
		This method should be called after a received transaction in order to generate the new UTXOs that are produced from this TX.
		'''

		if not self.is_hashed:
			raise Exception("Transaction is not hashed yet.")

		#Calculate the sum of TransactionInputs in order to caluclate the change that will be returned back to the sender
		total_coins_sent = 0
		for i in self.transaction_inputs:
			total_coins_sent += i.value

		if total_coins_sent < self.amount:
			raise Exception("Something went wrong. This transcation does not involve enough coins to cover the transfered amount.")

		#Calculate change for sender. Remember self.amount is the amount that the receiver will get
		change_for_sender = total_coins_sent - self.amount

		#Produce two UTXOs by creating two TransactionOutput object that will be saved in self.transaction_outputs list
		#Conventionally, recipient always takes index_arg = 0 and sender always takes index_arg = 1 
		if change_for_sender > 0:
			tx_output_recipient = TransactionOutput(self.transaction_id,0,self.receiver_address,self.amount)
			tx_output_sender = TransactionOutput(self.transaction_id,1,self.sender_address,change_for_sender)
			self.transaction_outputs = [tx_output_recipient,tx_output_sender]
		else:
			tx_output_recipient = TransactionOutput(self.transaction_id,0,self.receiver_address,self.amount)
			self.transaction_outputs = [tx_output_recipient]			


class TransactionOutput:

	def __init__(self, tx_id, index_arg, recipient_arg, amount_arg):

		#unique id of output = the unique output of transaction together with an index
		#index will be 0 for the output that changed ownership after the transaction
		#and 1 for the change that were returned to the original owner
		#type: tuple (bytes,int)
		self.output_id = (tx_id,index_arg)

		#transaction_id of the TX from which this UTXO was produced
		#type: bytes
		self.transaction_id = tx_id

		#address (public key) of the recipient
		#type: rsa.key.PublicKey
		self.recipient_address = recipient_arg

		#amount of coins transfered
		#type: float
		self.value = amount_arg

	def __str__(self):
		return f"output_id: {self.output_id} | recipient: {self.recipient_address} | value: {self.value}"

class TransactionInput:

	def __init__(self, utxo: TransactionOutput):

		#utxo parameter is a TransactionOutput object

		#the id of the UTXO from which this input was created
		#type: tuple (bytes,int)
		self.previous_output_id = utxo.output_id

		#transaction_id of the TX from which this UTXO was produced
		#type: bytes
		self.transaction_id = utxo.transaction_id

		#address (public key) of the recipient
		#type: rsa.key.PublicKey
		self.recipient_address = utxo.recipient_address

		#amount of coins transfered
		#type: float
		self.value = utxo.value

	def reproduce_utxo(self):
		return TransactionOutput(self.transaction_id, self.previous_output_id[1], self.recipient_address, self.value)