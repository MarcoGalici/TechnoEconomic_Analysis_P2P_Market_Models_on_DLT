from Networks import readNet as rnet
from Networks import setPPnet as ppnet
from Networks import runpf as rpf
import flex_market as flex
import copy as cp
import secrets
from eth_account import Account
import pandas as pd
import numpy as np
import time
import eval_file as ef
from statistics import mean


class Participant():
    def __int__(self, _add, _balance, _prvt_key, _node):
        self.add = _add
        self.balance = _balance
        self.prvtkey = _prvt_key
        self.node = _node

    def transfer(self, _amount, _flag):
        if _flag:
            if self.balance <= 0:
                pass
                # raise Warning('Balance not sufficient!!!')
            self.balance -= _amount
        else:
            self.balance += _amount

    def offer(self, _mu, _sigma, _howManyNumbers):
        """Le offerte dei partecipanti avranno come media il valore medio tra il costo di acquisto dell'energia dalla
        rete e il costo di acquisto dalla rete. Infine come std dev assumeranno un valore pari a 1/3 della deviazione
        tra la media ed il valore massimo, che sarà pari al costo di acqusito dalla rete."""
        return np.random.normal(_mu, _sigma, _howManyNumbers)

    def setAddr(self):
        priv = secrets.token_hex(32)
        private_key = "0x" + priv
        acct = Account.from_key(private_key)
        return acct.address, private_key


class DAmarket():
    def __init__(self, class_pf, network, buyER, sellER, cl_contract, neg_time):
        self.class_pf = class_pf
        self.net = cp.deepcopy(network)
        self.nuser = self.net.bus
        self.list_p = self._setparticipants()
        self.k_addrs = list(self.list_p.keys())
        self.sellGrid = sellER
        self.buyGrid = buyER
        self.book = dict()
        self.col = ['ID', 'address', 'node', 'price', 'amount']
        self.contracts = dict()
        self.class_contract = cl_contract
        self.list_time = dict()
        self.negotiation_t = neg_time

    def _setparticipants(self):
        """Crea lista dei partecipanti"""
        list_p = dict()
        for _nu in self.nuser.iterrows():
            p = cp.deepcopy(Participant())
            addrs_p, prvt_key_p = p.setAddr()
            p.add = addrs_p
            if float(_nu[1].name) == 0:
                p.balance = 1e5
            else:
                p.balance = 1e3
            p.prvtkey = prvt_key_p
            p.node = float(_nu[1].name)
            list_p[addrs_p] = p
        return list_p

    def marketoffers(self, bus_data, _iter):
        """Create offers and update book on the market"""
        adrs_so = self.k_addrs[0]
        df_b = list()
        df_s = list()

        # Il mercato si apre
        mu = (self.buyGrid - self.sellGrid) / 2
        sigma = (self.buyGrid - mu) / 3

        idx = 0
        rand_list = sorted(list(self.list_p.values()), key=lambda k: np.random.random())
        for _entity in rand_list:
            if _entity.add != adrs_so:
                # Iniziamo a contare il tempo prima del clearing
                start = time.time()

                # Offerta in PREZZO
                # "[0]" perché altrimenti estrae un vettore di 1 elemento
                off_price = abs(_entity.offer(mu, sigma, 1)[0])

                # Offerta in QUANTITA'
                # Consideriamo ogni peer come se fosse una singola entità.
                # Quindi vuol dire che l'offerta/richiesta di energia sul mercato sarà pari
                # alla differenza tra generazione e consumo.
                off_amount = round(bus_data.net_p_mw[_entity.node - 1], 7) * 1e3  # Trasformiamo in kW
                if off_amount > 0 and off_amount != 0:
                    df_b.append(['Node' + str(_entity.node), _entity.add, _entity.node, off_price, off_amount])
                elif off_amount < 0 and off_amount != 0:
                    df_s.append(['Node' + str(_entity.node), _entity.add, _entity.node, off_price, -off_amount])

                # Inseriamo il tempo iniziale di piazzamento offerte nella lista dei tempi
                self.list_time[_entity.add] = start
                # Incrementa indice
                idx += 1

        # Il mercato si chiude
        self.book['buyer'] = pd.DataFrame(df_b, columns=self.col)
        self.book['seller'] = pd.DataFrame(df_s, columns=self.col)

    def matching(self, _iter):
        """Esegui il matching delle offerte pubblicate nel mercato"""
        # Create list in _iter keys dictionary
        self.contracts[_iter] = list()

        if self.book['seller'].empty:
            # NESSUN OFFERTA DI VENDITA
            # Tutti pagano la quota standard di ACQUISTO DALLA RETE

            # ---------Trasferiamo i contanti [BUYER - SO]---------
            self._transfermoney(flag=0, _iter=_iter, book=self.book, pun=0, zn_price=0)

        elif self.book['buyer'].empty:
            # NESSUN OFFERTA DI ACQUISTO
            # Tutti pagano la quota standard di VENDITA ALLA RETE

            # ---------Trasferiamo i contanti [SELLER - SO]---------
            self._transfermoney(flag=1, _iter=_iter, book=self.book, pun=0, zn_price=0)

        else:
            # PRESENZA DI OFFERTE DI VENDITA
            # Intersezione delle curve di domanda e offerta

            # -------Solve Graph Intersection---------
            zonal_prices, zonal_demand = list(), list()
            eq_energy, marg_price, _intersc = self._intersection(self.book)

            zonal_prices.append(marg_price[0])
            zonal_demand.append(eq_energy[0])

            # --------------Evaluate PUN--------------
            # *** PUN pari a media ponderata
            pun = self._evalpun(zonal_prices, zonal_demand)

            # Definisci utenti infra-marginali ed extra-marginali
            zn_table = self._deftable([self.book], marg_price[0], eq_energy[0], _intersc)

            # ---------Trasferiamo i contanti per gli utenti che entrano nel mercato----------
            self._transfermoney(flag=2, _iter=_iter, book=zn_table[0]['infra-marginal'], pun=pun, zn_price=zonal_prices[0])

            # ---------Trasferiamo i contanti ai prezzi Energy Retailer [BUYER - SO]----------
            self._transfermoney(flag=0, _iter=_iter, book=zn_table[0]['extra-marginal'], pun=0, zn_price=0)

            # ---------Trasferiamo i contanti ai prezzi Energy Retailer [SELLER - SO]---------
            self._transfermoney(flag=1, _iter=_iter, book=zn_table[0]['extra-marginal'], pun=0, zn_price=0)

    def _deftable(self, listBook, market_p, market_q, _c):
        """Definisci utenti infra-marginali ed utenti extra-marginali"""
        # Creiamo una copia del libro delle offerte (chiamato infra-marginal book)
        inframarg_book = cp.deepcopy(self.book)
        # Creiamo una copia del libro delle offerte (chiamato extra-marginal book)
        extramarg_book = cp.deepcopy(self.book)

        zn_table = dict()
        idx = 0
        for _table in listBook:
            if _table['buyer'].empty or _table['seller'].empty:
                # Siccome in questa zona non ci sono abbastanza consumatori/produttori allora definisci subito
                # gli acquirenti/venditori extra-marginali
                zn_table[idx] = {'infra-marginal': {'buyer': pd.DataFrame(), 'seller': pd.DataFrame()},
                                 'extra-marginal': _table}
            else:
                if _c:
                    sum_energyDemand = 0
                    sum_energySupply = 0
                    last_buyer = len(_table['buyer'])
                    last_seller = len(_table['seller'])
                    diff_energyb_if = _table['buyer'].amount[len(_table['buyer']) - 1]
                    diff_energyb_ef = _table['buyer'].amount[len(_table['buyer']) - 1]
                    diff_energys_if = _table['seller'].amount[len(_table['seller']) - 1]
                    diff_energys_ef = _table['seller'].amount[len(_table['seller']) - 1]

                    for i in range(len(_table['buyer'])):
                        sum_energyDemand += _table['buyer'].amount[i]
                        if _table['buyer'].price[i] >= market_p:
                            last_buyer = i + 1
                            if sum_energyDemand <= market_q:
                                diff_energyb_if = _table['buyer'].amount[i]
                                diff_energyb_ef = 0
                            else:
                                diff_energyb_if = _table['buyer'].amount[i] - (sum_energyDemand - market_q)
                                diff_energyb_ef = _table['buyer'].amount[i] - market_q
                                break
                        else:
                            break

                    for i in range(len(_table['seller'])):
                        sum_energySupply += _table['seller'].amount[i]
                        if _table['seller'].price[i] <= market_p:
                            last_seller = i + 1
                            if sum_energySupply <= market_q:
                                diff_energys_if = _table['seller'].amount[i]
                                diff_energys_ef = 0
                            else:
                                diff_energys_if = _table['seller'].amount[i] - (sum_energySupply - market_q)
                                diff_energys_ef = _table['seller'].amount[i] - diff_energys_if
                                break
                        else:
                            break

                    # Eliminaimo le offerte che non entrano nel mercato (attori extra-marginali)
                    inframarg_book['buyer'] = _table['buyer'].drop(range(last_buyer, len(_table['buyer'])))
                    inframarg_book['seller'] = _table['seller'].drop(range(last_seller, len(_table['seller'])))

                    # Cambia l'ultimo buyer amount
                    inframarg_book['buyer'].amount[len(inframarg_book['buyer']) - 1] = diff_energyb_if
                    # Cambia l'ultimo seller amount
                    inframarg_book['seller'].amount[len(inframarg_book['seller']) - 1] = diff_energys_if

                    # Eliminaimo le offerte che entrano nel mercato (attori infra-marginali)
                    extramarg_book['buyer'] = _table['buyer'].drop(range(0, last_buyer - 1)).reset_index(drop=True)
                    extramarg_book['seller'] = _table['seller'].drop(range(0, last_seller - 1)).reset_index(drop=True)

                    # Cambia il primo buyer amount
                    extramarg_book['buyer'].amount[0] = extramarg_book['buyer'].amount[0] - diff_energyb_if
                    # Cambia il primo seller amount
                    extramarg_book['seller'].amount[0] = extramarg_book['seller'].amount[0] - diff_energys_if

                    # Elimina gli elementi che sono nulli nel campo "amount"
                    extramarg_book['buyer'].drop(
                        index=list(extramarg_book['buyer'][extramarg_book['buyer'].amount <= 10e-3].index), inplace=True)
                    extramarg_book['seller'].drop(
                        index=list(extramarg_book['seller'][extramarg_book['seller'].amount <= 10e-3].index), inplace=True)

                    zn_table[idx] = {'infra-marginal': inframarg_book, 'extra-marginal': extramarg_book}

                else:
                    inframarg_book['buyer'] = pd.DataFrame()
                    inframarg_book['seller'] = pd.DataFrame()

                    extramarg_book['buyer'] = _table['buyer']
                    extramarg_book['seller'] = _table['seller']

                    zn_table[idx] = {'infra-marginal': inframarg_book, 'extra-marginal': extramarg_book}

            idx += 1

        return zn_table

    def _sumordbook(self, data):
        x = [sum(data[:i + 1]) for i in range(len(data))]
        return x

    def _intersection(self, ledger):
        """Prepara i dati per le curve di demand e supply"""
        # Ordina il libro delle offerte
        ledger['buyer'] = ledger['buyer'].sort_values('price', ascending=False, ignore_index=True)
        ledger['seller'] = ledger['seller'].sort_values('price', ascending=True, ignore_index=True)

        cost_d = ledger['buyer'].price
        cost_g = ledger['seller'].price
        Pdemand = ledger['buyer'].amount
        Pgeneration = ledger['seller'].amount

        # D = self._sumordbook(Pdemand)
        # S = self._sumordbook(Pgeneration)

        price_gen = np.array(cost_g)
        price_dem = np.array(cost_d)

        # Nel caso non ci siano intersezioni ci possono essere 2 casi:
        # 1) Poca Generazione che non copre domanda. In questo caso essendo la domanda elastica, allora il venditore
        #    riuscirà a vendere tutto e la domanda sarà coperta solo dal quantitativo offerto dal seller.
        # 2) Troppa generazione e poca domanda. In questo caso abbiamo High Supply e Low Demand.
        #    Quindi abbiamo troppa produzione a prezzi elevati.In questo caso avviene una deflezione
        #    del mercato (contrario di inflazione).
        x = 0
        y = 0
        _c = False
        if price_dem[0] >= price_gen[0]:
            # Caso in cui ci può essere intersezione del mercato , anche poca generazione.
            # Nel secondo caso essendo la domanda elastica allora esiste comunque un intersezione
            mrk_q, mrk_p = self._findintrsc2(np.array(Pgeneration), np.array(Pdemand), np.array(cost_g), np.array(cost_d))
            x = np.array([mrk_q])
            y = np.array([mrk_p])
            _c = True

        elif price_dem[0] < price_gen[0]:
            # Non c'è intersezione
            x = np.array([sum(Pdemand)])
            y = np.array([0])
            _c = False
            # if demand[-1] < supply[-1]:
            #     # --------Troppa generazione a prezzi elevati--------
            #     # *** Il prezzo zonale è fissato al prezzo dell'ultimo venditore
            #     y = np.array([ledger['seller'].price[len(ledger['seller']) - 1]])
            #     # *** La domanda è pari a tutta la quantità venduta dai venditori
            #     x = np.array([sum(ledger['seller'].amount)])
            #
            # elif demand[-1] > supply[-1]:
            #     # ---------Poca generazione a prezzi elevati---------
            #     # *** Il prezzo zonale è fissato al prezzo più basso dei compratori
            #     y = np.array([ledger['buyer'].price[len(ledger['buyer']) - 1]])
            #     # *** La domanda è pari a tutta la richiesta dei compratori
            #     x = np.array([sum(ledger['buyer'].amount)])

        return x, y, _c

    def _findintrsc2(self, supply, demand, supply_c, demand_c):
        """Trova intersezione delle curve di domanda e supply"""
        market_q = 0
        market_p = 0
        idxD = 0
        idxS = 0

        while min(sum(supply), sum(demand)) > 0:
            if demand_c[idxD] >= supply_c[idxS]:
                if demand[idxD] >= supply[idxS]:
                    diff = demand[idxD] - supply[idxS]
                    market_q += supply[idxS]
                    market_p = min(supply_c[idxS], demand_c[idxD])
                    supply[idxS] = 0
                    demand[idxD] = diff
                    idxS += 1
                else:
                    diff = supply[idxS] - demand[idxD]
                    market_q += demand[idxD]
                    market_p = min(supply_c[idxS], demand_c[idxD])
                    demand[idxD] = 0
                    supply[idxS] = diff
                    idxD += 1
            else:
                break

        return market_q, market_p

    def _evalpun(self, zonal_prices, zonal_demand):
        pun = sum([zonal_prices[i] * zonal_demand[i] for i in range(len(zonal_prices))])/sum(zonal_demand)
        return pun

    def _transfermoney(self, flag, _iter, book, pun, zn_price):
        """---Trasferiamo il contante da partecipante a SO---"""
        time_sleep = np.random.uniform(low=0.5, high=2, size=1)[0]
        if flag == 0:
            # ---Trasferiamo il contante da BUYER a SO---
            for _user in book['buyer'].iterrows():
                if _user[1].address != self.list_p[self.k_addrs[0]].add:
                    self.list_p[_user[1].address].transfer(self.buyGrid * _user[1].amount, True)
                    self.list_p[self.k_addrs[0]].transfer(self.buyGrid * _user[1].amount, False)
                    # Salviamo i contratti

                self._insertContract(
                    _adrsS=self.k_addrs[0],
                    _adrsB=_user[1].address,
                    _price_kWh=self.buyGrid,
                    _bidPrice=_user[1].price,
                    _cost=self.buyGrid * _user[1].amount,
                    _amnt=_user[1].amount,
                    _iter=_iter,
                    _clear_t=time.time() + self.negotiation_t + time_sleep - self.list_time[_user[1].address],
                    _totflexCost=0,
                    _flx_prcS=0,
                    _flx_prcB=0,
                    _flxUS=0,
                    _flxDS=0,
                    _flxUB=0,
                    _flxDB=0,
                    _flexU_slack=0,
                    _flexD_slack=0)

        elif flag == 1:
            # ---Trasferiamo il contante da SO a SELLER---
            for _user in book['seller'].iterrows():
                if _user[1].address != self.list_p[self.k_addrs[0]].add:
                    self.list_p[_user[1].address].transfer(self.sellGrid * _user[1].amount, False)
                    self.list_p[self.k_addrs[0]].transfer(self.sellGrid * _user[1].amount, True)
                    # Salviamo i contratti
                    self._insertContract(
                        _adrsS=_user[1].address,
                        _adrsB=self.k_addrs[0],
                        _price_kWh=self.sellGrid,
                        _bidPrice=_user[1].price,
                        _cost=-self.sellGrid * _user[1].amount,
                        _amnt=-_user[1].amount,
                        _iter=_iter,
                        _clear_t=time.time() + self.negotiation_t + time_sleep - self.list_time[_user[1].address],
                        _totflexCost=0,
                        _flx_prcS=0,
                        _flx_prcB=0,
                        _flxUS=0,
                        _flxDS=0,
                        _flxUB=0,
                        _flxDB=0,
                        _flexU_slack=0,
                        _flexD_slack=0)

        elif flag == 2:
            # MARKET INTERSECTION
            for _buyer in book['buyer'].iterrows():
                if _buyer[1].address != self.list_p[self.k_addrs[0]].add:
                    self.list_p[_buyer[1].address].transfer(pun * _buyer[1].amount, True)
                    # Salviamo i contratti
                    self._insertContract(
                        _adrsS=self.k_addrs[0],
                        _adrsB=_buyer[1].address,
                        _price_kWh=pun,
                        _bidPrice=_buyer[1].price,
                        _cost=pun * _buyer[1].amount,
                        _amnt=_buyer[1].amount,
                        _iter=_iter,
                        _clear_t=time.time() + self.negotiation_t + time_sleep - self.list_time[_buyer[1].address],
                        _totflexCost=0,
                        _flx_prcS=0,
                        _flx_prcB=0,
                        _flxUS=0,
                        _flxDS=0,
                        _flxUB=0,
                        _flxDB=0,
                        _flexU_slack=0,
                        _flexD_slack=0)

            for _seller in book['seller'].iterrows():
                if _seller[1].address != self.list_p[self.k_addrs[0]].add:
                    self.list_p[_seller[1].address].transfer(zn_price * _seller[1].amount, False)
                    # Salviamo i contratti
                    self._insertContract(
                        _adrsS=_seller[1].address,
                        _adrsB=self.k_addrs[0],
                        _price_kWh=zn_price,
                        _bidPrice=_seller[1].price,
                        _cost=-zn_price * _seller[1].amount,
                        _amnt=-_seller[1].amount,
                        _iter=_iter,
                        _clear_t=time.time() + self.negotiation_t + time_sleep - self.list_time[_seller[1].address],
                        _totflexCost=0,
                        _flx_prcS=0,
                        _flx_prcB=0,
                        _flxUS=0,
                        _flxDS=0,
                        _flxUB=0,
                        _flxDB=0,
                        _flexU_slack=0,
                        _flexD_slack=0)

    def _insertContract(self, _adrsS, _adrsB, _price_kWh, _bidPrice, _cost, _amnt, _iter, _clear_t,
                        _totflexCost, _flx_prcS, _flx_prcB, _flxUS, _flxDS, _flxUB, _flxDB, _flexU_slack, _flexD_slack):
        """Insert Contract into class"""
        # contract class
        _cc = cp.deepcopy(self.class_contract)

        _cc.add_seller = _adrsS
        _cc.add_buyer = _adrsB
        _cc.price_kWh = _price_kWh
        _cc.bid_price = _bidPrice
        _cc.cost = _cost
        _cc.amount = _amnt
        _cc.interval = _iter
        _cc.clear_time = _clear_t
        _cc.total_flexCost = _totflexCost
        _cc.flex_priceSeller = _flx_prcS
        _cc.flex_priceBuyer = _flx_prcB
        _cc.flex_UprovideS = _flxUS
        _cc.flex_DprovideS = _flxDS
        _cc.flex_UprovideB = _flxUB
        _cc.flex_DprovideB = _flxDB
        _cc.flexU_slack = _flexU_slack
        _cc.flexD_slack = _flexD_slack
        self.contracts[_iter].append(_cc)

    def includeflexcost(self, _t, _vFlex, _vSlack, _Summary, _fsp):
        """Includi i dati del servizio di flessibilitò nei contratti."""
        tot_kWh = sum([i.amount for i in self.contracts[_t]])

        flx_ul = 'FSP Flex Upward Loads [kWh]'
        flx_dl = 'FSP Flex Downward Loads [kWh]'
        flx_ug = 'FSP Flex Upward Gens [kWh]'
        flx_dg = 'FSP Flex Downward Gens [kWh]'

        # Calcola il costo di flessibilità totale
        pg_totC = 'tot Costs [Euro]'
        pg_fuL = 'flex UP LOADs'
        pg_fuG = 'flex UP GENs'
        pg_fdL = 'flex DOWN LOADs'
        pg_fdG = 'flex DOWN GENs'
        pg_sU = 'flex Slack UP'
        pg_sD = 'flex Slack DW'
        _totFlexCost = _Summary[pg_fuL][pg_totC] + _Summary[pg_fuG][pg_totC] + _Summary[pg_fdL][pg_totC] \
                       + _Summary[pg_fdG][pg_totC] + _Summary[pg_sU][pg_totC] + _Summary[pg_sD][pg_totC]

        # NOTA: Gli utenti offrono sempre considerando un certo range di sicurezza che serve proprio
        # per rispondere nel caso ci sia l'introduzione delle variabili slack
        slack_up = sum(_vSlack['Flex not supplied UP']) / len(_fsp)
        slack_dw = sum(_vSlack['Flex not supplied DW']) / len(_fsp)

        # Determina la flessibilità offerta da ogni partecipante
        flx_p = dict()
        for _i in range(len(self.list_p)):
            if self.list_p[self.k_addrs[_i]].add != self.list_p[self.k_addrs[0]].add:
                flex_upL = _vFlex[flx_ul]['Node' + str(_i)]
                flex_upG = _vFlex[flx_ug]['Node' + str(_i)]
                flex_dwL = _vFlex[flx_dl]['Node' + str(_i)]
                flex_dwG = _vFlex[flx_dg]['Node' + str(_i)]
                if (self.list_p[self.k_addrs[_i]].node - 1) in list(_fsp)[0]:
                    # Se l'utente si trova tra i partecipanti che hanno offerto nel mercato allora inserisci la slack
                    flx_p[self.k_addrs[_i]] = [flex_upL, flex_upG, flex_dwL, flex_dwG, slack_up, slack_dw]
                else:
                    # Se l'utente non si trovasse tra i partecipanti che hanno offerto nel mercato
                    # allora vuol dire che non vuole offrire flessibilità quindi non caricare slack
                    flx_p[self.k_addrs[_i]] = [flex_upL, flex_upG, flex_dwL, flex_dwG, 0, 0]

        # Modifica i dati dei contratti per includere i costi del servizio di flessibilità
        for _contr in range(len(self.contracts[_t])):
            _cc = self.contracts[_t][_contr]
            buyer_adrs = _cc.add_buyer
            seller_adrs = _cc.add_seller

            _mflex2transf = 0
            if buyer_adrs != self.list_p[self.k_addrs[0]].add and seller_adrs == self.list_p[self.k_addrs[0]].add:
                # Solo il Buyer partecipa a creare una contingenza.
                # Pertanto sarà caricato di una tassa per la provvigione della flessibilità solo il Buyer.
                _mflex2transf = _totFlexCost * (_cc.amount / tot_kWh)

                # Riduciamo la quantità di energia consumata nel contratto di una quota pari alla slack_up
                _cc.amount -= flx_p[buyer_adrs][4]
                # Aumentiamo la quantità di energia consumata nel contratto di una quota pari alla slack_down
                _cc.amount += flx_p[buyer_adrs][5]

            elif buyer_adrs == self.list_p[self.k_addrs[0]].add and seller_adrs != self.list_p[self.k_addrs[0]].add:
                # Solo il Seller partecipa a creare una contingenza.
                # Pertanto sarà caricato di una tassa per la provvigione della flessibilità solo il Seller
                _mflex2transf = _totFlexCost * (_cc.amount / tot_kWh)

                # Aumentiamo la quantità di energia prodotta nel contratto di una quota pari alla slack_up
                _cc.amount += flx_p[seller_adrs][4]
                # Riduciamo la quantità di energia prodotta nel contratto di una quota pari alla slack_down
                _cc.amount -= flx_p[seller_adrs][5]

            # Aggiungiamo il costo totale di flessibilità in ogni contratto
            # self.Contract[_t][_contr].total_flexCost = _totFlexCost
            _cc.total_flexCost = _totFlexCost

            # ------ Verifica che il BUYER non sia il SO ------
            if buyer_adrs != self.list_p[self.k_addrs[0]].add:
                # Il servizio UP di flex è pari alla somma del servizio UP dei carichi più quello dei generatori - BUYER
                up_flxB = flx_p[buyer_adrs][0] + flx_p[buyer_adrs][1]
                # Il servizio DW di flex è pari alla somma del servizio DW dei carichi più quello dei generatori - BUYER
                dw_flxB = flx_p[buyer_adrs][2] + flx_p[buyer_adrs][3]

                # Riduci il bilancio del Buyer
                self.list_p[buyer_adrs].transfer(_mflex2transf, True)

                # Inserisci le informazioni sul mercato di flessibilità nel contratto relativo
                _cc.flex_priceBuyer = _mflex2transf
                _cc.flex_UprovideB = up_flxB
                _cc.flex_DprovideB = dw_flxB

                # Il servizio di flessibilità slack sarà una somma tra il servizio tra Buyer e Seller.
                # Nel caso uno dei due fosse il SO allora si sommerebbe zero
                _cc.flexU_slack += flx_p[buyer_adrs][4]
                _cc.flexD_slack += flx_p[buyer_adrs][5]

            else:
                # Nel caso l'indirizzo del buyer fosse il SO, allora metti a zero
                _cc.flex_priceBuyer = 0
                _cc.flex_UprovideB = 0
                _cc.flex_DprovideB = 0
                _cc.flexU_slack += 0
                _cc.flexD_slack += 0

            # ------ Verifica che il SELLER non sia il SO ------
            if seller_adrs != self.list_p[self.k_addrs[0]].add:
                # Il servizio UP di flex è pari alla somma del servizio UP dei carichi più quello dei generatori - SEL
                up_flxS = flx_p[seller_adrs][0] + flx_p[seller_adrs][1]
                # Il servizio DW di flex è pari alla somma del servizio DW dei carichi più quello dei generatori - SEL
                dw_flxS = flx_p[seller_adrs][2] + flx_p[seller_adrs][3]

                # Riduci il bilancio del Seller
                self.list_p[seller_adrs].transfer(_mflex2transf, True)

                # Inserisci le informazioni sul mercato di flessibilità nel contratto relativo
                _cc.flex_priceSeller = _mflex2transf
                _cc.flex_UprovideS = up_flxS
                _cc.flex_DprovideS = dw_flxS

                # Il servizio di flessibilità slack sarà una somma tra il servizio tra Buyer e Seller.
                # Nel caso uno dei due fosse il SO allora si sommerebbe zero
                _cc.flexU_slack += flx_p[seller_adrs][4]
                _cc.flexD_slack += flx_p[seller_adrs][5]

            else:
                # Nel caso l'indirizzo del seller fosse il SO, allora metti a zero
                _cc.flex_priceSeller = 0
                _cc.flex_UprovideS = 0
                _cc.flex_DprovideS = 0
                _cc.flexU_slack += 0
                _cc.flexD_slack += 0

    def set_list(self):
        list_c = {'ID': list(),
                  'adrsB': list(),
                  'adrsS': list(),
                  'cost': list(),
                  'amount': list(),
                  'price [euro/kWh]': list(),
                  'price bid': list(),
                  'interval': list(),
                  'clear_time': list(),
                  'flex_priceBuyer': list(),
                  'flex_priceSeller': list(),
                  'flex_UprovideS': list(),
                  'flex_DprovideS': list(),
                  'flex_UprovideB': list(),
                  'flex_DprovideB': list(),
                  'flexU_slack': list(),
                  'flexD_slack': list(),
                  'total_flex_Cost': list()}

        for _k in self.contracts.keys():
            _idx = 0
            for _value in self.contracts[_k]:
                list_c['ID'].append(_idx)
                list_c['adrsB'].append(_value.add_buyer)
                list_c['adrsS'].append(_value.add_seller)
                list_c['cost'].append(_value.cost)
                list_c['amount'].append(_value.amount)
                list_c['price [euro/kWh]'].append(_value.price_kWh)
                list_c['price bid'].append(_value.bid_price)
                list_c['interval'].append(_value.interval)
                list_c['clear_time'].append(_value.clear_time)
                list_c['flex_priceSeller'].append(_value.flex_priceSeller)
                list_c['flex_priceBuyer'].append(_value.flex_priceBuyer)
                list_c['flex_UprovideS'].append(_value.flex_UprovideS)
                list_c['flex_DprovideS'].append(_value.flex_DprovideS)
                list_c['flex_UprovideB'].append(_value.flex_UprovideB)
                list_c['flex_DprovideB'].append(_value.flex_DprovideB)
                list_c['flexU_slack'].append(_value.flexU_slack)
                list_c['flexD_slack'].append(_value.flexD_slack)
                list_c['total_flex_Cost'].append(_value.total_flexCost)
                _idx += 1
            # Agiungiamo spazio
            list_c['ID'].append('-')
            list_c['adrsB'].append('-')
            list_c['adrsS'].append('-')
            list_c['cost'].append('-')
            list_c['amount'].append('-')
            list_c['price [euro/kWh]'].append('-')
            list_c['price bid'].append('-')
            list_c['interval'].append('-')
            list_c['clear_time'].append('-')
            list_c['flex_priceBuyer'].append('-')
            list_c['flex_priceSeller'].append('-')
            list_c['flex_UprovideS'].append('-')
            list_c['flex_DprovideS'].append('-')
            list_c['flex_UprovideB'].append('-')
            list_c['flex_DprovideB'].append('-')
            list_c['flexU_slack'].append('-')
            list_c['flexD_slack'].append('-')
            list_c['total_flex_Cost'].append('-')

        return list_c

    def collecttimes(self):
        list_times = list()

        for _k in self.contracts.keys():
            _idx = 0
            list_time_interval = list()
            for _value in self.contracts[_k]:
                list_time_interval.append(_value.clear_time)
            list_times.append(mean(list_time_interval))

        return list_times


class Contract():
    def __init__(self):
        self.add_seller = None
        self.add_buyer = None
        self.price_kWh = None
        self.bid_price = None
        self.cost = None
        self.amount = None
        self.interval = None
        self.clear_time = None
        self.total_flexCost = None
        self.flex_priceSeller = None
        self.flex_priceBuyer = None
        self.flex_UprovideS = None
        self.flex_DprovideS = None
        self.flex_UprovideB = None
        self.flex_DprovideB = None
        self.flexU_slack = None
        self.flexD_slack = None


if __name__ == "__main__":
    # Set fixed SEED
    np.random.seed(0)

    # File per salvataggio - Double Auction market (Centralised)
    filename_DA = 'Results\centralmarket_test251122.xlsx'

    # Load network from files
    net = rnet.Net(r'Networks\16nodes_wcong.dat')

    # Create and extract PandaPower network from files
    pp_network = ppnet.PPnet(net).emptyNet

    # Create class for running personalize power flow
    c_pf = rpf.pf(pp_network, net)

    # Power Factor of the net
    pf_net = 0.96
    # Congestion management market class
    cm = flex.CMmarket(pf_net, pp_network, Participant())

    # Prezzo di vendita alla rete
    # 25 EURO/MWh (0.025 EURO/kWh)
    sellGrid = 0.025
    # Prezzo di acquisto dalla rete
    # 400 EURO/MWh (0.4 EURO/kWh)
    buyGrid = 0.4

    # Negotiation time [30 minuti]
    neg_time = 30 * 60

    m = DAmarket(c_pf, pp_network, buyGrid, sellGrid, Contract(), neg_time)

    # --------------------Mercato------------------
    list_ctimes = dict()
    for _i in range(1):
        print(' ')
        print(_i)
        for t in range(c_pf.time):
            print(t)

            # ------Set previous SoC and Profiles------
            bus_data = c_pf.evalsoc(t)

            # -----------Set Offer and Sort------------
            m.marketoffers(bus_data, t)

            # ----------------Matching-----------------
            m.matching(t)

            # Run PF
            check_cons = c_pf.runPF(bus_data)

            # Get result of network
            c_pf.savevar(t)
            res_net = c_pf.res_net

            if not check_cons:
                # Inseriamo una copia della rete pandapower (con i risultati del power flow) dentro la classe CMmarket
                cm.net = cp.deepcopy(c_pf.network_pp)

                # Elaborate parameters for optimisation
                nCONG, DSO_Req = cm.evalnet(t, res_net)

                # Make Offers (only loads can offer flexibility - "for now")
                fsp = cm.makeoffer(res_net, t)

                # Optimise
                model_opt, vars = cm.setOptModel(nCONG, DSO_Req, False)
                v_flex, v_slack, summary = cm.extractOptValue(vars, nCONG)

                # Include flexibility
                new_load_profile, new_gen_profile = cm.addflexibility(res_net['p_Load'][t], res_net['p_Gen'][t], vars)

                # Get new bus data
                bus_data_aft = cm.getnewbusdata(bus_data, new_load_profile, new_gen_profile, res_net, t)

                # Run PF
                check_cons = c_pf.runPF(bus_data_aft)
                c_pf.change_elementDf(t, pd.Series(res_net['p_Store'][t]), new_gen_profile, new_load_profile)

                # Save data
                c_pf.savevar(t)

                # Distribute costs towards peers included in the P2P market
                m.includeflexcost(t, v_flex, v_slack, summary, fsp)

        # Save times on Excel
        # list_ctimes[_i] = m.collecttimes()
    # c_pf.write_excel(filename=filename_DA, sheet_name='Time Eval', data=list_ctimes)
    # exit()

    # Extract list of contracts
    list_cntr = m.set_list()

    # Save list of contracts on Excel
    c_pf.write_excel(filename=filename_DA, sheet_name='Market times', data=list_cntr)

    # Save data on DataFrame
    c_pf.savedf()

    # Extract Data
    df_net = c_pf.df_net

    # Save networks results on Excel
    c_pf.write_excel(filename=filename_DA, sheet_name='ppeer_kw',       data=df_net['ppeer_df'])
    c_pf.write_excel(filename=filename_DA, sheet_name='qpeer_kvar',     data=df_net['qpeer_df'])
    c_pf.write_excel(filename=filename_DA, sheet_name='vmpeer',         data=df_net['vmpeer_df'])
    c_pf.write_excel(filename=filename_DA, sheet_name='pLoad',          data=df_net['pLoad_df'])
    c_pf.write_excel(filename=filename_DA, sheet_name='pGen',           data=df_net['pGen_df'])
    c_pf.write_excel(filename=filename_DA, sheet_name='pStore',         data=df_net['pStore_df'])
    c_pf.write_excel(filename=filename_DA, sheet_name='pVeicolo',       data=df_net['pVeicolo_df'])
    c_pf.write_excel(filename=filename_DA, sheet_name='SoC_storage',    data=df_net['SoC_df'])
    c_pf.write_excel(filename=filename_DA, sheet_name='Line Loading',   data=df_net['line_df'])
    c_pf.write_excel(filename=filename_DA, sheet_name='Trafo Loading',  data=df_net['trafo_df'])

    # Save Users and addresses on Excel
    c_pf.write_excel(filename=filename_DA,
                     sheet_name='User addresses',
                     data={'address': m.k_addrs, 'node': [m.list_p[k].node for k in m.list_p.keys()]})

    eval_class = ef.eval(m.contracts, buyGrid, sellGrid, m.list_p, m.list_p[list(m.list_p.keys())[0]].add, c_pf)
    eval_class.evalSW(False)
    eval_class.evalCQR(False)
    eval_class.writexlsx(filename=filename_DA, sheet_name='Comparison SW',      data=eval_class.SW)
    eval_class.writexlsx(filename=filename_DA, sheet_name='Comparison DW',      data=eval_class.DW)
    eval_class.writexlsx(filename=filename_DA, sheet_name='Comparison CQR',     data=eval_class.CQR)
    eval_class.writexlsx(filename=filename_DA, sheet_name='Comparison tot bid', data=eval_class.tot_bid)
