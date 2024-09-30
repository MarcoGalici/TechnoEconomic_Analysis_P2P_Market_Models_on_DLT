import pandas as pd
from os.path import exists
from tkinter.messagebox import showwarning as shw


class debug_bck():
    def __init__(self):
        self.df_mnemonics = pd.DataFrame.from_dict({
            'STOP': [0, 0, 0],
            'ADD': [2, 1, 3],
            'MUL': [2, 1, 5],
            'SUB': [2, 1, 3],
            'DIV': [2, 1, 5],
            'SDIV': [2, 1, 5],
            'MOD': [2, 1, 5],
            'SMOD': [2, 1, 5],
            'ADDMOD': [3, 1, 8],
            'MULMOD': [3, 1, 8],
            'EXP': [2, 1, 60],
            'SIGNEXTEND': [2, 1, 5],
            'LT': [2, 1, 3],
            'GT': [2, 1, 3],
            'SLT': [2, 1, 3],
            'SGT': [2, 1, 3],
            'EQ': [2, 1, 3],
            'ISZERO': [1, 1, 3],
            'AND': [2, 1, 3],
            'OR': [2, 1, 3],
            'XOR': [2, 1, 3],
            'NOT': [1, 1, 3],
            'BYTE': [2, 1, 3],
            'SHL': [2, 1, 3],
            'SHR': [2, 1, 3],
            'SAR': [2, 1, 3],
            'KECCAK256': [2, 1, 36],
            'ADDRESS': [0, 1, 2],
            'BALANCE': [1, 1, 2600],
            'ORIGIN': [0, 1, 2],
            'CALLER': [0, 1, 2],
            'CALLVALUE': [0, 1, 2],
            'CALLDATALOAD': [1, 1, 3],
            'CALLDATASIZE': [0, 1, 2],
            'CALLDATACOPY': [3, 0, 6],
            'CODESIZE': [0, 1, 2],
            'CODECOPY': [3, 0, 6],
            'GASPRICE': [0, 1, 2],
            'EXTCODESIZE': [1, 1, 2600],
            'EXTCODECOPY': [2, 1, 2603],
            'RETURNDATASIZE': [0, 1, 2],
            'RETURNDATACOPY': [3, 0, 6],
            'EXTCODEHASH': [1, 1, 2600],
            'BLOCKHASH': [1, 1, 20],
            'COINBASE': [0, 1, 2],
            'TIMESTAMP': [0, 1, 2],
            'NUMBER': [0, 1, 2],
            'DIFFICULTY': [0, 1, 2],
            'GASLIMIT': [0, 1, 2],
            'CHAINID': [0, 1, 2],
            'SELFBALANCE': [0, 1, 5],
            'POP': [1, 0, 2],
            'MLOAD': [1, 1, 3],
            'MSTORE': [2, 0, 3],
            'MSTORES': [2, 0, 3],
            'SLOAD': [1, 1, 2200],
            'SSTORE': [2, 0, 25100],
            'JUMP': [1, 0, 8],
            'JUMPI': [2, 0, 10],
            'PC': [0, 1, 2],
            'MSIZE': [0, 1, 2],
            'GAS': [0, 1, 2],
            'JUMPDEST': [0, 0, 1],
            'PUSH': [0, 1, 3],
            'DUP1': [1, 2, 3],
            'DUP2': [2, 3, 3],
            'DUP3': [3, 4, 3],
            'DUP4': [4, 5, 3],
            'DUP5': [5, 6, 3],
            'DUP6': [6, 7, 3],
            'DUP7': [7, 8, 3],
            'DUP8': [8, 9, 3],
            'DUP9': [9, 10, 3],
            'DUP10': [10, 11, 3],
            'DUP11': [11, 12, 3],
            'DUP12': [12, 13, 3],
            'DUP13': [13, 14, 3],
            'DUP14': [14, 15, 3],
            'DUP15': [15, 16, 3],
            'DUP16': [16, 17, 3],
            'SWAP1': [2, 2, 3],
            'SWAP2': [3, 3, 3],
            'SWAP3': [4, 4, 3],
            'SWAP4': [5, 5, 3],
            'SWAP5': [6, 6, 3],
            'SWAP6': [7, 7, 3],
            'SWAP7': [8, 8, 3],
            'SWAP8': [9, 9, 3],
            'SWAP9': [10, 10, 3],
            'SWAP10': [11, 11, 3],
            'SWAP11': [12, 12, 3],
            'SWAP12': [13, 13, 3],
            'SWAP13': [14, 14, 3],
            'SWAP14': [15, 15, 3],
            'SWAP15': [16, 16, 3],
            'SWAP16': [17, 17, 3],
            'LOG1': [2, 0, 383],
            'LOG2': [3, 0, 758],
            'LOG3': [4, 0, 1133],
            'LOG4': [5, 0, 1508],
            'LOG5': [6, 0, 1883],
            'CREATE': [3, 1, 32000],
            'CALL': [7, 1, 13900],
            'CALLCODE': [7, 1, 13900],
            'RETURN': [2, 0, 0],
            'DELEGATECALL': [6, 1, 13900],
            'CREATE2': [4, 1, 32030],
            'STATICCALL': [6, 1, 13900],
            'REVERT': [2, 0, 0],
            'INVALID': [0, 0, 0],
            'SELFDESTRUCT': [1, 0, 32600],
        })
        self.centralised = {'bcond': list(),
                            'getMV': list(),
                            'getV': list(),
                            'intrsc': list(),
                            'sorting': list(),
                            'makeOffer': list(),
                            'min': list(),
                            'sum': list(),
                            'transfer': list(),
                            'register': list()}
        self.distributed = {'bcond': list(),
                            'intrsc': list(),
                            'sorting': list(),
                            'makeOffer': list(),
                            'transfer': list(),
                            'register': list()}

    def write_excel(self, filename, sheet_name, data):
        """Trasforma un dizionario in un dataframe e scrivi i valori dentro un file excel"""

        df1 = pd.DataFrame.from_dict(data, orient='index', columns=['delta', 'alpha', 'gas'])
        # print(df1)
        file_exists = exists(filename)
        try:
            if file_exists:
                with pd.ExcelWriter(filename, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                        df1.to_excel(writer, sheet_name=sheet_name)
            else:
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                        df1.to_excel(writer, sheet_name=sheet_name)
        except PermissionError:
            shw(title='Warning', message='Close file Excel in order to save data!!!')
            self.write_excel(filename, sheet_name, data)

    def savedata(self, filename, market_design, sheet):
        with open(filename) as f:
            lines = f.readlines()

        delta = list()
        alpha = list()
        gas = list()
        for _index in lines:
            try:
                delta.append(self.df_mnemonics[_index.split()[1]][0])
                alpha.append(self.df_mnemonics[_index.split()[1]][1])
                gas.append(self.df_mnemonics[_index.split()[1]][2])
            except KeyError:
                delta.append(self.df_mnemonics['PUSH'][0])
                alpha.append(self.df_mnemonics['PUSH'][1])
                gas.append(self.df_mnemonics['PUSH'][2])

        if market_design:
            self.centralised[sheet].append(sum(delta))
            self.centralised[sheet].append(sum(alpha))
            self.centralised[sheet].append(sum(gas))
        else:
            self.distributed[sheet].append(sum(delta))
            self.distributed[sheet].append(sum(alpha))
            self.distributed[sheet].append(sum(gas))


if __name__ == "__main__":
    dbck = debug_bck()
    dbck.savedata(r'Debug\Centralised\min.txt', True, 'min')
    dbck.savedata(r'Debug\Centralised\sum.txt', True, 'sum')
    dbck.savedata(r'Debug\Centralised\boundary_conditions_central.txt', True, 'bcond')
    dbck.savedata(r'Debug\Centralised\getMinValues.txt', True, 'getMV')
    dbck.savedata(r'Debug\Centralised\getValues.txt', True, 'getV')
    dbck.savedata(r'Debug\Centralised\intersection_central.txt', True, 'intrsc')
    dbck.savedata(r'Debug\Centralised\sorting_central.txt', True, 'sorting')
    dbck.savedata(r'Debug\Centralised\makeOffer_central.txt', True, 'makeOffer')
    dbck.savedata(r'Debug\Centralised\transfer_central.txt', True, 'transfer')
    dbck.savedata(r'Debug\Centralised\register_central.txt', True, 'register')

    dbck.savedata(r'Debug\Distributed\boundary_conditions_distributed.txt', False, 'bcond')
    dbck.savedata(r'Debug\Distributed\intersection_distributed.txt', False, 'intrsc')
    dbck.savedata(r'Debug\Distributed\sorting_distributed.txt', False, 'sorting')
    dbck.savedata(r'Debug\Distributed\makeOffer_distributed.txt', False, 'makeOffer')
    dbck.savedata(r'Debug\Distributed\transfer_distributed.txt', False, 'transfer')
    dbck.savedata(r'Debug\Distributed\register_distributed.txt', False, 'register')

    dbck.write_excel('Results\debug.xlsx', 'centralised', dbck.centralised)
    dbck.write_excel('Results\debug.xlsx', 'distributed', dbck.distributed)
    pass
