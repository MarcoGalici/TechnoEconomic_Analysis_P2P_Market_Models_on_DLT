from web3 import HTTPProvider, Web3


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
        print(is_connected)
        return is_connected

    def newContract(self, abi, bytecode, acc, time, timeInit):
        Contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        tx_hash = Contract.constructor(acc, time, timeInit).transact({'from': acc})
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

    # Carica dati in Blokchcian
    def setIssuer(self, acc, contract):
        return contract.functions.setIssuer().transact({'from': acc})

    def makeOffer(self, acc, contract, _id, _price, _electricityAmount, _bs):
        return contract.functions.makeOffer(_id, _bs, _price, _electricityAmount).transact({'from': acc})

    def uploadptdf(self, acc, contract, _user1, _user2, _valptdf):
        return contract.functions.uploadptdf(_valptdf, _user1, _user2).transact({'from': acc})

    def setIndexTime(self, acc, contract, _idx):
        return contract.functions.setIndexTime(_idx).transact({'from': acc})

    def performMatching(self, acc, contract):
        return contract.functions._performMatching().transact({'from': acc})

    # Funzioni getter
    def getParticipantInformations(self, contract, _issuer):
        return contract.functions.getParticipantInformations(_issuer).call()

    def getMarketTime(self, contract):
        return contract.functions.getMarketTime().call()

    def getIdxTime(self, contract):
        return contract.functions.getIdxTime().call()

    def getBiddingTime(self, contract):
        return contract.functions.getIdxTime().call()

    def getOffersInfo(self, contract, _acc):
        return contract.functions.getOffersInfo(_acc).call()

    def getTimestamp(self, contract):
        return contract.functions.getTimestamp().call()

    def getptdf(self, contract):
        return contract.functions.getptdf().call()

    def balanceOf(self, contract):
        return contract.functions.balanceOf().call()

    # Funzioni generiche per blockchain
    def gasUsed(self, tx_hash):
        receipt = self.w3.eth.waitForTransactionReceipt(tx_hash)
        return receipt.gasUsed

    def gasPrice(self):
        return self.w3.eth.gas_price

    def waitReceipt(self, tx_hash):
        return self.w3.eth.waitForTransactionReceipt(tx_hash)
