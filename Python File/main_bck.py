from main import runpf_net, readres, fillmarketbook
from contracts.da_contractData import abi, bytecode, adrs_contract
from fcnbck import Blockchain_Fcn
import numpy as np
import pandas as pd
import time


def signup(bck_class, Contract, net, Accounts, master_acc):
    """Sign Up each peer of the network.
    NOTE: Only 9 user are admitted since only 10 address are available."""
    ext_grid = net.ext_grid.index
    bus = net.bus.index
    # Set difference betweeen ext_grid and bus
    dif1 = np.setdiff1d(ext_grid, bus)
    dif2 = np.setdiff1d(bus, ext_grid)
    users = np.concatenate((dif1, dif2))

    dict_users = dict()
    dict_users['Node'] = list()
    dict_users['Account'] = list()

    j = 1
    for i in Accounts:
        if i is not master_acc and j <= len(users):
            if Contract.functions.meters(i).call()[1] == 0:
                # Add new user only if the account is not yet registered
                tx_hash_setissuer = bck_class.setIssuer(i, Contract)
                bck_class.waitReceipt(tx_hash_setissuer)
                time.sleep(3)

            # Link each node to the Account on bck
            dict_users['Node'].append(j)
            dict_users['Account'].append(i)
            j += 1

    df_users = pd.DataFrame.from_dict(dict_users)
    return df_users


if __name__ == "__main__":
    filename = r"Input\albacete_feeder.xlsx"
    filename_profile = r"Input\profile.xlsx"
    purch_pr = 0.4  # euro/kWh
    sell_pr = 0.025  # euro/kWh

    net = runpf_net(filename, filename_profile)

    df_res = readres(net)

    # Define Data of contract
    http = "192.168.0.193"
    port = "8545"
    abi = abi.abi
    bytecode = bytecode.bytecode
    Address_Contract = adrs_contract.Address_contract
    master_acc = 0

    # Create variables for interactions
    fcnclass = Blockchain_Fcn()
    fcnclass.set_Connection(http, port)
    fcnclass.is_Connected()

    # Call contract already uploaded on blockchain
    Contract = fcnclass.callContract(abi, Address_Contract)
    Accounts = fcnclass.get_Accounts()

    # Set Master prices
    if Contract.functions.buyGrid().call() * (10 ** -3) == 0:
        # Set prices only if they are not yet set
        tx_hash_setPrices = fcnclass.setPrices(Accounts[master_acc], Contract, int(purch_pr * (10 ** 3)), int(sell_pr * (10 ** 3)))
        fcnclass.waitReceipt(tx_hash_setPrices)

    # Register each user
    df_users = signup(fcnclass, Contract, net, Accounts, Accounts[master_acc])

    # Create contract dictionary
    cntrs = dict()

    # Start Simulation
    for _iter in range(len(df_res)):
        m_book = fillmarketbook(df_res.loc[_iter], purch_pr, sell_pr, _iter)

        # Place offer on Blockchain
        if not m_book['buyer'].empty:
            for _b in m_book['buyer'].iterrows():
                pr_buyer = int(_b[1].price * (10 ** 3))
                amnt_buyer = int(_b[1].amount * (10 ** 3))
                adrs_buyer = df_users.Account[df_users.Node == _b[1].Node].array[0]
                tx_hash_makeOff = fcnclass.makeOffer(adrs_buyer, Contract, True, pr_buyer, amnt_buyer)
                fcnclass.waitReceipt(tx_hash_makeOff)
                time.sleep(3)

        if not m_book['seller'].empty:
            for _b in m_book['seller'].iterrows():
                pr_seller = int(_b[1].price * (10 ** 3))
                amnt_seller = int(_b[1].amount * (10 ** 3))
                adrs_seller = df_users.Account[df_users.Node == _b[1].Node].array[0]
                tx_hash_makeOff = fcnclass.makeOffer(adrs_seller, Contract, False, pr_seller, amnt_seller)
                fcnclass.waitReceipt(tx_hash_makeOff)
                time.sleep(3)

        # ----------------Matching-----------------
        tx_hash_match = fcnclass.matching(Accounts[master_acc], Contract)
        fcnclass.waitReceipt(tx_hash_match)
        time.sleep(5)

        # Extract Contracts
        n_cntrs = len(m_book['buyer']) + len(m_book['seller'])
        iter_contracts = dict()
        iter_contracts['buyer'] = list()
        iter_contracts['seller'] = list()
        iter_contracts['price'] = list()
        iter_contracts['amount'] = list()
        for _h in range(n_cntrs):
            try:
                contracts = Contract.functions.contracts(_iter, _h).call()
                iter_contracts['buyer'].append(contracts[0])
                iter_contracts['seller'].append(contracts[1])
                iter_contracts['price'].append(contracts[2] * (10 ** -3))
                iter_contracts['amount'].append(contracts[3] * (10 ** -3))
                print(contracts)
            except ValueError:
                break
        # Create DataFrame for visualization
        cntrs[_iter] = pd.DataFrame.from_dict(iter_contracts)

        # Increase Index Time
        tx_hash_idxTime = fcnclass.setIndexTime(Accounts[master_acc], Contract, int(_iter+1))
        fcnclass.waitReceipt(tx_hash_idxTime)
        time.sleep(5)