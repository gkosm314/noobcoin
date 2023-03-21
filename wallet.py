import rsa
import base64
import transaction
import block
import json

class Wallet:

	def __init__(self):
		(pub_k, priv_k) = rsa.newkeys(512)
		self.public_key = pub_k
		self.private_key = priv_k


def public_key2str(public_key):
	if type(public_key) == int: # for genesis block
		return public_key
	else:
		return public_key.save_pkcs1().decode("utf-8")

def str2public_key(public_key_str):
	return rsa.PublicKey.load_pkcs1(public_key_str)

def serialize_public_keys_table(table):
	# table = {id: public_key}
	return dict((k, public_key2str(v)) for k, v in table.items())

def deserialize_public_keys_table(table):
	# table = json.loads(table)
	print(type(table))
	return dict((k, str2public_key(v)) for k, v in table.items())

def serialize_network_info_table(table):
	# table = {public_key: (ip, port)}
	return dict((public_key2str(k), v) for k, v in table.items())

def deserialize_network_info_table(table):
	# table = json.loads(table)
	print(type(table))
	return dict((str2public_key(k), v) for k, v in table.items())

def serialize_block(b):
	return {
		"index": b.index,
		"timestamp": b.timestamp,
		"transactions": [serialize_transaction(t) for t in b.transactions],
		"previous_hash": b.previous_hash.hex(),
		"current_hash": b.current_hash.hex(),
		"nonce": b.nonce
	}

def deserialize_block(s):
	b = block.Block(s["index"], bytes.fromhex(s["previous_hash"]))
	b.timestamp = s["timestamp"]
	b.transactions = [deserialize_transaction(t) for t in s["transactions"]]
	b.current_hash = bytes.fromhex(s["current_hash"])
	b.nonce = s["nonce"]
	return b

def serialize_transaction(tx):
	return {
		"sender_address": public_key2str(tx.sender_address),
		"receiver_address": public_key2str(tx.receiver_address),
		"amount": tx.amount,
		"transaction_inputs": tx.transaction_inputs,
		"signature": tx.signature.hex(), 
		"transaction_id": tx.transaction_id.hex()
	}

def deserialize_transaction(s):
	args = {
		"sender_address": str2public_key(s["sender_address"]),
		"receiver_address": str2public_key(s["receiver_address"]),
		"amount": s["amount"],
		"transaction_inputs": s["transaction_inputs"]
	}
	tx = transaction.Transaction(args)
	tx.signature = bytes.fromhex(s["signature"])
	tx.transaction_id = bytes.fromhex(s["transaction_id"])

	return tx


if __name__ == "__main__":
	import json
 
	# public_key1, private_key = rsa.newkeys(2048)
	# pub_str = public_key2str(public_key1)
	# json.dumps(pub_str)
	# assert public_key1 == str2public_key(pub_str)

	# public_keys_table = {}
	# for i in range(4):
	# 	public_key1, _ = rsa.newkeys(2048)
	# 	public_keys_table[i] = public_key1
	# serialized = serialize_public_keys_table(public_keys_table)
	# assert deserialize_public_keys_table(serialized) == public_keys_table

	# net_info_table = {}
	# for i in range(4):
	# 	public_key1, _ = rsa.newkeys(2048)
	# 	net_info_table[public_key1] = ("ip", "port")
	# serialized = serialize_network_info_table(net_info_table)
	# j = json.dumps(serialized)
	# print(j)
	# de_j = json.loads(j)
	# print("-------------------------------------\n\n\n\n")
	# print(de_j)
	# assert deserialize_network_info_table(de_j) == net_info_table

	##############################

	# import block
	# b = block.Block(4, rsa.compute_hash("a".encode(), 'SHA-1'))
	# b.current_hash = rsa.compute_hash("b".encode(), 'SHA-1')
	# b.nonce = 1
	# s = serialize_block(b)
	
	# assert b.index == s['index']
	# assert b.previous_hash == bytes.fromhex(s['previous_hash'])
	# assert b.timestamp == s['timestamp']
	# assert b.transactions == [deserialize_transaction(t) for t in s['transactions']]
	# assert b.current_hash == bytes.fromhex(s['current_hash'])
	# assert b.nonce == s['nonce']
	
	# print(vars(b))

	##############################

	# import transaction

	# public_key1, _ = rsa.newkeys(2048)
	# args = {
	# 	'sender_address': public_key1,
	# 	'receiver_address': public_key1,
	# 	'amount': 100,
	# 	'transaction_inputs': []
	# }
	# tx = transaction.Transaction(args)
	# tx.signature = rsa.compute_hash("a".encode(), 'SHA-1')
	# tx.transaction_id = rsa.compute_hash("a".encode(), 'SHA-1')

	# print(vars(tx))
	# print(vars(deserialize_transaction(serialize_transaction(tx))))

	import jsonpickle
	import block
	
	b = block.Block(4, rsa.compute_hash("a".encode(), 'SHA-1'))
	b.current_hash = rsa.compute_hash("b".encode(), 'SHA-1')
	b.nonce = 1
	
	frozen = jsonpickle.encode(b)
	print(frozen)
	thawed = jsonpickle.decode(frozen)
	print(thawed)