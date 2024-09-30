from web3 import HTTPProvider, Web3
from contracts.da_contractData import abi, bytecode, adrs_contract


class Blockchain_Fcn:
    def __init__(self):
        self.w3 = None

    def set_Connection(self, http, port):
        w3 = Web3(HTTPProvider('http://' + http + ':' + port + '/'))
        # Save w3 class as global variable for all the methods
        self.w3 = w3
        return w3

    def is_Connected(self):
        is_connected = self.w3.isConnected()
        if not is_connected:
            print("Blockchain not online")
            exit()

    def newContract(self, abi, bytecode, acc):
        Contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        tx_hash = Contract.constructor(acc).transact({'from': acc})
        tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash)
        CONTRACT = self.w3.eth.contract(address=tx_receipt.contractAddress, abi=abi)
        return CONTRACT, tx_hash, tx_receipt.contractAddress

    def callContract(self, abi, Contract_Adrs):
        CONTRACT = self.w3.eth.contract(address=Contract_Adrs, abi=abi)
        return CONTRACT

    def get_Accounts(self):
        Accounts = self.w3.eth.accounts
        return Accounts

    def get_Function(self, Contract):
        Function = Contract.all_functions()
        return Function

    def get_contracts(self, contract, indexTime, cntr_n):
        return contract.functions.contracts(indexTime, cntr_n).call()

    # Load data on Blokchcian
    # --- Master functions ---
    def setPrices(self, acc, contract, _bGrid, _sGrid):
        return contract.functions.setPrices(_bGrid, _sGrid).transact({'from': acc})

    # --- Token functions ---
    def balanceOf(self, contract, tokenOwner):
        return contract.functions.balanceOf(tokenOwner).call()

    def transfer(self, acc, contract, sender, receiver, numTokens, amount):
        return contract.functions.transfer(sender, receiver, numTokens, amount).transact({'from': acc})

    # --- Participant functions ---
    def setIssuer(self, acc, contract):
        return contract.functions.setIssuer().transact({'from': acc})

    def getParticipantInformations(self, contract, _issuer):
        return contract.functions.getParticipantInformations(_issuer).call()

    # --- Place offer functions ---
    def makeOffer(self, acc, contract, _bs, _price, _quantity):
        return contract.functions.makeOffer(_bs, _price, _quantity).transact({'from': acc})

    def getOffersInfo(self, contract, _sender):
        return contract.functions.getOffersInfo(_sender).call()

    def setIndexTime(self, acc, contract, _idxTime):
        return contract.functions.setIndexTime(_idxTime).transact({'from': acc})

    # --- Auction mechanism functions ---
    def matching(self, acc, contract):
        return contract.functions.matching().transact({'from': acc})

    # --- Genral functions Blockchain
    def gasUsed(self, tx_hash):
        receipt = self.w3.eth.waitForTransactionReceipt(tx_hash)
        return receipt.gasUsed

    def gasPrice(self):
        return self.w3.eth.gas_price

    def waitReceipt(self, tx_hash):
        return self.w3.eth.waitForTransactionReceipt(tx_hash)


if __name__ == "__main__":
    # Define Data of contract
    http = "192.168.0.193"
    port = "8545"
    abi = abi.abi
    bytecode = bytecode.bytecode
    master_acc = 0

    # Create variables for interactions
    fcnclass = Blockchain_Fcn()
    fcnclass.set_Connection(http, port)
    fcnclass.is_Connected()

    # Get accounts
    Accounts = fcnclass.get_Accounts()
    print("Blockchain accounts")
    print(Accounts)

    print(" ")
    print('Select the following options: ')
    print('[0] - Load new contract')
    print('[1] - Call contract')
    _flag1 = input('Enter your option: ')
    if _flag1 is "0":
        _flag = False
    else:
        _flag = True

    if _flag:
        Address_Contract = adrs_contract.Address_contract
        # Call contract already uploaded on blockchain
        Contract = fcnclass.callContract(abi, Address_Contract)
    else:
        # Upload contract with constructor variables
        Contract, tx_hash_Contract, Address_Contract = fcnclass.newContract(abi, bytecode, Accounts[master_acc])

    # Visualise function on contract
    print(" ")
    print("Contract Functions")
    print(fcnclass.get_Function(Contract))

    print(" ")
    print("Main Participant: ", Accounts[master_acc])
    print(" ")
    print("Contract address: ", Address_Contract)