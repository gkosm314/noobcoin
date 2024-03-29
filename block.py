import time
import transaction
import rsa
from config import *

def starts_with_difficulty_zeros(next_hash, difficulty):
    next_hash = int.from_bytes(next_hash, "big")   
    mask = (1<<(160-difficulty))-1
    mask &= next_hash
    res = next_hash^mask == 0
    return res

class Block:
  
    def __init__(self, block_index_arg, previous_hash_arg):
        #index of this block
        #type: int
        self.index = block_index_arg

        #timestamp that informs us about when this block was created
        #type: float - seconds since start of epoch
        self.timestamp = time.time()

        #list of transactions included in this block
        #type: list of 'transaction' objects
        self.transactions = []

        #hash of the previous block in the blockchain
        #type: bytes
        self.previous_hash = previous_hash_arg 

    def __str__(self):
        '''
        Implements string method that is called when you attempt to print() the block.
        Creates an empty string and appends a string for each transaction in the block.
        '''

        s = f"BLOCK #{self.index}"
        for tx in self.transactions:
            s = s + str(tx) + "\n"
        return s

    def add_transaction(self, tx: transaction):
        '''
        Assumption: the transaction is already validated.
        Adds the transaction to the block and returns 
        Note: if we use multithreading, this method should be called atomically
        '''

        #We cannot add the tx if the block will have more than the allowed transactions after the addition
        if len(self.transactions) + 1 > capacity:
            raise Exception('Block already full, no more transactions can be added.')

        #Add the transaction to the block by appending it to the transactions list
        self.transactions.append(tx)

    def full(self):
        '''Returns True if the block is full and False otherwise'''

        if len(self.transactions) < capacity:
            return False
        else:
            return True

    def mine(self):
        '''
        This method does not check that the block is full. It is responsibility of the caller to perform the check.
        Finds proof-of-work for this block and updates nonce and current hash fields accordingly.
        '''

        candidate_nonce = 0
        candidate_msg_to_hash = str((self.index, self.timestamp, self.transactions, self.previous_hash, candidate_nonce))
        next_hash = rsa.compute_hash(candidate_msg_to_hash.encode(), 'SHA-1')

        #Note: this one-liner is also used at valid_hash_of_block() in node.py. In case it is changed, change it there too!    
        while not starts_with_difficulty_zeros(next_hash, difficulty):
            #try another nonce
            candidate_nonce += 1
            candidate_msg_to_hash = str((self.index, self.timestamp, self.transactions, self.previous_hash, candidate_nonce))
            next_hash = rsa.compute_hash(candidate_msg_to_hash.encode(), 'SHA-1')

        #nonce for this block
        #type: int
        self.nonce = candidate_nonce

        #message that will be hashed by those who receive this block in order to calculate the hash
        #type: string
        self.msg_to_hash = candidate_msg_to_hash

        #hash of this block
        #type: bytes
        self.current_hash = next_hash

    def toJSON(self):
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': [t.toJSON() for t in self.transactions],
            'previous_hash': self.previous_hash.hex(),
            'current_hash': self.current_hash.hex(),
            'nonce': self.nonce
        }