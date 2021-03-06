import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4
import requests
from flask import Flask, jsonify, request, render_template, redirect
from abc import ABC, abstractmethod


class ProofOfWork(ABC):
    def __init__(self):
        self.__proof

    def add_proof(self, value):
        self.__proof += value
        return self.__proof

    def set_proof(self, value):
        self.__proof = value
        return self.__proof

    def get_proof(self):
        return self.__proof

    @abstractmethod
    def proof_of_work(self, last_block): pass

    @staticmethod
    def valid_proof(last_proof, proof, last_hash):
        """
        Validates the Proof
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :param last_hash: <str> The hash of the Previous Block
        :return: <bool> True if correct, False if not.
        """

        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


class Blockchain(ProofOfWork):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.current_user = []
        self.__currentIndex = 1
        self.nodes = set()
        # Create the genesis block
        self.new_block(previous_hash='1', proof=100)

    def proof_of_work(self, last_block):
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes
         - Where p is the previous proof, and p' is the new proof
         
        :param last_block: <dict> last Block
        :return: <int>
        """

        last_proof = last_block['proof']
        last_hash = self.hash(last_block)

        self.set_proof(0)
        while self.valid_proof(last_proof, self.get_proof(), last_hash) is False:
            self.add_proof(1)

        return self.get_proof()

    def valid_chain(self, chain):
        """"
        Determine if a given blockchain is valid
        :param chain: A blockchain
        :return: True if valid, False if not
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            last_block_hash = self.hash(last_block)
            if block['previous_hash'] != last_block_hash:
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof'], last_block_hash):
                return False

            last_block = block
            print(self.__currentIndex)
            current_index += 1

        return True

    def new_block(self, proof, previous_hash):
        """
        Create a new Block in the Blockchain
        :param proof: The proof given by the Proof of Work algorithm
        :param previous_hash: Hash of previous Block
        :return: New Block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'user':self.current_user,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Reset the current list of transactions
        self.current_transactions = []
        self.current_user = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        try:
            self.current_transactions.append({
                'sender': sender,
                'recipient': recipient,
                'amount': float(amount),
            })
            return self.last_block['index'] + 1
        except Exception as e:
            print(e)
            return self.last_block['index']

    def new_user(self, name, surname, email):
        new_id = self.last_user_id + 1
        try:
            self.current_user.append({
                'id': new_id,
                'name': name,
                'surname': surname,
                'email': email,
            })
            return self.last_block['index'] + 1
        except Exception as e:
            print(e)
            return self.last_block['index']

    @property
    def last_block(self):
        return self.chain[-1]

    @property
    def last_user_id(self):
        return len(self.current_user)

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block
        :param block: Block
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def register_node(self, address):
        """
        Add a new node to the list of nodes
        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """

        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:

            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')

    def resolve_conflicts(self):

        neighbours = self.nodes
        new_chain = None

        max_length = len(self.chain)

        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True

        return False

    def validate(self):
        """"
            Determine if a given blockchain is valid
        :param chain: A blockchain
        :return: True if valid, False if not
        """
        neighbours = self.nodes
        new_chain = None

        max_length = len(self.chain)

        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                last_block = chain[0]
                current_index = 1

                while current_index < len(chain):
                    block = chain[current_index]

                    last_block_hash = self.hash(last_block)
                    if block['previous_hash'] != last_block_hash:
                        return False

                    last_block = block
                    current_index += 1

        return True


class ProofValid(Blockchain):
    def validate(self):

        neighbours = self.nodes
        new_chain = None

        max_length = len(self.chain)

        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                chain = response.json()['chain']

                last_block = chain[0]
                current_index = 1

                while current_index < len(chain):
                    if not self.valid_proof(last_block['proof'], block['proof'], last_block_hash):
                        return False

                    last_block = block
                    current_index += 1

        return True
