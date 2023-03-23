import rsa
import base64

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

def public_keys_table2json(table):
	# table = {id: public_key}
	return dict((k, public_key2str(v)) for k, v in table.items())

def network_info_table2json(table):
	# table = {public_key: (ip, port)}
	return dict((public_key2str(k), v) for k, v in table.items()) 