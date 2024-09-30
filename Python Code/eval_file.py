import copy as cp


class eval():
    def __init__(self, list_c, buyER, sellER, participant_list, adrs_so, class_writer):
        self.list_contracts = cp.deepcopy(list_c)
        self.sellGrid = sellER
        self.buyGrid = buyER
        self.list_p = cp.deepcopy(participant_list)
        self.c_writer = cp.deepcopy(class_writer)
        self.adrs_so = adrs_so
        self.SW = {'Social-Welfare': list(), 'Time': list()}
        self.DW = {'Deficit': list(), 'Time': list()}
        self.CQR = {'Clear Quantity Ratio [-]': list(), 'Clear Quantity Ratio [kWh]': list(), 'Cleared Quantity': list(), 'Tot Quantity': list(), 'Time': list()}
        self.tot_bid = {'Number bids': list(), 'Number cleared bids': list(), 'Time': list()}

    def evalSW(self, flag):
        if flag:
            # Mercato Decentralizzato
            for _k in self.list_contracts.keys():
                self.DW['Time'].append(_k)
                self.SW['Time'].append(_k)
                self.SW['Social-Welfare'].insert(_k, 0)
                self.DW['Deficit'].insert(_k, 0)
                for _i in self.list_contracts[_k]:
                    if _i.price_kWh == self.buyGrid:
                        self.DW['Deficit'][_k] += (_i.price_kWh - _i.bid_priceB) * _i.amount
                    elif _i.price_kWh == self.sellGrid:
                        self.DW['Deficit'][_k] += (_i.bid_priceS - _i.price_kWh) * _i.amount
                    else:
                        self.SW['Social-Welfare'][_k] += (_i.bid_priceB - _i.price_kWh) * _i.amount
                        self.SW['Social-Welfare'][_k] += (_i.price_kWh - _i.bid_priceS) * _i.amount
        else:
            # Mercato Centralizzato
            for _k in self.list_contracts.keys():
                self.DW['Time'].append(_k)
                self.SW['Time'].append(_k)
                self.SW['Social-Welfare'].insert(_k, 0)
                self.DW['Deficit'].insert(_k, 0)
                for _i in self.list_contracts[_k]:
                    if _i.price_kWh == self.buyGrid or _i.price_kWh == self.sellGrid:
                        if _i.amount > 0:
                            self.DW['Deficit'][_k] += (_i.price_kWh - _i.bid_price) * abs(_i.amount)
                        else:
                            self.DW['Deficit'][_k] += (_i.bid_price - _i.price_kWh) * abs(_i.amount)
                    else:
                        if _i.amount > 0:
                            self.SW['Social-Welfare'][_k] += (_i.bid_price - _i.price_kWh) * abs(_i.amount)
                        else:
                            self.SW['Social-Welfare'][_k] += (_i.price_kWh - _i.bid_price) * abs(_i.amount)

    def evalCQR(self, _flag):
        for _k in self.list_contracts.keys():
            q_clear = 0
            tot_q = 0
            list_bidder = list()
            tot_bids = 0
            tot_cbids = 0
            if _flag:
                dict_totq = {_j: 0 for _j in self.list_p.keys()}
                dict_totcq = {_j: 0 for _j in self.list_p.keys()}
                for _i in self.list_contracts[_k]:
                    flag = 0
                    if _i.price_kWh == self.buyGrid or _i.price_kWh == self.sellGrid:
                        pass
                    else:
                        flag += 1
                        tot_cbids += 1
                        dict_totcq[_i.add_buyer] += abs(_i.amount)
                        dict_totcq[_i.add_seller] += abs(_i.amount)

                    if _i.add_buyer != self.adrs_so:
                        dict_totq[_i.add_buyer] += abs(_i.amount)
                    if _i.add_seller != self.adrs_so:
                        dict_totq[_i.add_seller] += abs(_i.amount)

                    if _i.add_buyer not in list_bidder or _i.add_seller not in list_bidder:
                        if _i.add_buyer != self.adrs_so:
                            list_bidder.append(_i.add_buyer)
                        if _i.add_seller != self.adrs_so:
                            list_bidder.append(_i.add_seller)
                        tot_bids += 1

                q_clear = sum(list(dict_totcq.values()))
                tot_q = sum(list(dict_totq.values()))

            else:
                for _i in self.list_contracts[_k]:
                    flag = 0
                    tot_q += abs(_i.amount)
                    if _i.price_kWh == self.buyGrid or _i.price_kWh == self.sellGrid:
                        pass
                    else:
                        flag += 1
                        q_clear += abs(_i.amount)
                        tot_cbids += 1

                    if _i.add_buyer not in list_bidder or _i.add_seller not in list_bidder:
                        if _i.add_buyer != self.adrs_so:
                            list_bidder.append(_i.add_buyer)
                        if _i.add_seller != self.adrs_so:
                            list_bidder.append(_i.add_seller)
                        tot_bids += 1

            self.CQR['Clear Quantity Ratio [-]'].append(q_clear/tot_q)
            try:
                self.CQR['Clear Quantity Ratio [kWh]'].append(q_clear/tot_cbids)
            except ZeroDivisionError:
                self.CQR['Clear Quantity Ratio [kWh]'].append(0)
            self.CQR['Cleared Quantity'].append(q_clear)
            self.CQR['Tot Quantity'].append(tot_q)
            self.CQR['Time'].append(_k)

            self.tot_bid['Number bids'].append(tot_bids)
            self.tot_bid['Number cleared bids'].append(tot_cbids)
            self.tot_bid['Time'].append(_k)

    def writexlsx(self, filename, sheet_name, data):
        self.c_writer.write_excel(filename=filename, sheet_name=sheet_name, data=data)


if __name__ == "__main__":
    pass
