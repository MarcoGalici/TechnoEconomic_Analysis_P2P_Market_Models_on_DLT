from Networks import readNet as rnet
from Networks import setPPnet as ppnet
from Networks import runpf as rpf
import random
import copy as cp
import secrets
from eth_account import Account
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import LineString
import time
import eval_file as ef


class Participant():
    def __int__(self, _add, _balance, _prvt_key, _node):
        self.add = _add
        self.balance = _balance
        self.prvtkey = _prvt_key
        self.node = _node

    def transfer(self, _amount, _flag):
        if _flag:
            if self.balance <= 0:
                raise Warning('Balance not sufficient!!!')
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
    def __init__(self, class_pf, network, buyER, sellER, cl_contract):
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

    def _setparticipants(self):
        """Crea lista dei partecipanti"""
        list_p = dict()
        for _nu in self.nuser.iterrows():
            p = Participant()
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

    def marketoffers(self, bus_data):
        """Create offers and update book on the market"""
        adrs_so = self.k_addrs[0]
        df_b = list()
        df_s = list()

        # Il mercato si apre
        mu = (self.buyGrid - self.sellGrid) / 2
        sigma = (self.buyGrid - mu) / 3

        idx = 0
        rand_list = sorted(list(self.list_p.values()), key=lambda k: random.random())
        for _entity in rand_list:
            if _entity.add != adrs_so:
                # Attendiamo qualche istante random per caricare la nuova offerta
                # time.sleep(np.random.uniform(low=0.5, high=2.2, size=1))

                # Iniziamo a contare il tempo prima del clearing
                start = time.time()

                # Offerta in PREZZO
                # "[0]" perché altrimenti estrae un vettore di 1 elemento
                off_price = abs(_entity.offer(mu, sigma, 1)[0])

                # Offerta in QUANTITA'
                # Consideriamo ogni peer come se fosse una singola entità.
                # Quindi vuol dire che l'offerta/richiesta di energia sul mercato sarà pari
                # alla differenza tra generazione e consumo.
                off_amount = round(bus_data.net_p_mw[idx], 7) * 1e3  # Trasformiamo in kW
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

    def matching(self, _iter, bus_data):
        """Esegui il matching delle offerte pubblicate nel mercato"""
        # Create list in _iter keys dictionary
        self.contracts[_iter] = list()

        if self.book['seller'].empty:
            # NESSUN OFFERTA DI VENDITA
            # Tutti pagano la quota standard di ACQUISTO DALLA RETE

            check_cons = self.class_pf.runPF(bus_data)

            if not check_cons:
                zn_book = self._modbus(bus_data, not check_cons)
                _ = self._deftable(zn_book, sum(self.book['buyer'].price), sum(self.book['buyer'].amount))

            # ---------Trasferiamo i contanti [BUYER - SO]---------
            self._transfermoney(flag=0, _iter=_iter, book=self.book, pun=0, zn_price=0)

        elif m.book['buyer'].empty:
            # NESSUN OFFERTA DI ACQUISTO
            # Tutti pagano la quota standard di VENDITA ALLA RETE

            check_cons = self.class_pf.runPF(bus_data)

            if not check_cons:
                zn_book = self._modbus(bus_data, not check_cons)
                _ = self._deftable(zn_book, sum(self.book['seller'].price), sum(self.book['seller'].amount))

            # ---------Trasferiamo i contanti [SELLER - SO]---------
            self._transfermoney(flag=1, _iter=_iter, book=self.book, pun=0, zn_price=0)

        else:
            # PRESENZA DI OFFERTE DI VENDITA
            # Intersezione delle curve di domanda e offerta

            # -------Solve Graph Intersection---------
            zonal_prices, zonal_demand = list(), list()
            # eq_energy, marg_price = self._intrsc2curves(self.book, flag=True)
            eq_energy, marg_price = self._intersection(self.book)

            zonal_prices.append(marg_price[0])
            zonal_demand.append(eq_energy[0])

            # --------------Evaluate PUN--------------
            # *** PUN pari a media ponderata
            pun = self._evalpun(zonal_prices, zonal_demand)

            # -------------Check Congestion on the lines-------------
            check_cons = self.class_pf.runPF(bus_data)

            nbook = self._modbus(bus_data, not check_cons)
            if _iter > 5:
                print(' ')

            if not check_cons:
                zonal_prices, zonal_demand = list(), list()
                # --------Solve Graph Intersection per each zone--------
                for _zn in nbook:

                    if _zn['seller'].empty or _zn['buyer'].empty:
                        # *** Prezzo zonale fissato al prezzo di rete
                        zonal_prices.append(sellGrid)
                        zonal_demand.append(sum(_zn['buyer'].amount))
                    else:
                        eq_energy, marg_price = self._intersection(_zn)

                        zonal_prices.append(marg_price[0])
                        zonal_demand.append(eq_energy[0])

                # --------------Evaluate PUN--------------
                pun = self._evalpun(zonal_prices, zonal_demand)

                # Definisci utenti infra-marginali ed extra-marginali
                zn_table = self._deftable(nbook, marg_price[0], eq_energy[0])

                # ---------Trasferiamo i contanti per ogni zona di mercato----------

                for _zn in range(len(zn_table)):
                    # ---------Trasferiamo i contanti per gli utenti che entrano nel mercato----------
                    self._transfermoney(flag=2, _iter=_iter, book=zn_table[_zn]['infra-marginal'], pun=pun, zn_price=zonal_prices[_zn])

                    # ---------Trasferiamo i contanti ai prezzi Energy Retailer [BUYER - SO]----------
                    self._transfermoney(flag=0, _iter=_iter, book=zn_table[_zn]['extra-marginal'], pun=0, zn_price=0)

                    # ---------Trasferiamo i contanti ai prezzi Energy Retailer [SELLER - SO]---------
                    self._transfermoney(flag=1, _iter=_iter, book=zn_table[_zn]['extra-marginal'], pun=0, zn_price=0)

            else:
                # Definisci utenti infra-marginali ed extra-marginali
                zn_table = self._deftable(nbook, marg_price[0], eq_energy[0])

                # ---------Trasferiamo i contanti per gli utenti che entrano nel mercato----------
                self._transfermoney(flag=2, _iter=_iter, book=zn_table[0]['infra-marginal'], pun=pun, zn_price=zonal_prices[0])

                # ---------Trasferiamo i contanti ai prezzi Energy Retailer [BUYER - SO]----------
                self._transfermoney(flag=0, _iter=_iter, book=zn_table[0]['extra-marginal'], pun=0, zn_price=0)

                # ---------Trasferiamo i contanti ai prezzi Energy Retailer [SELLER - SO]---------
                self._transfermoney(flag=1, _iter=_iter, book=zn_table[0]['extra-marginal'], pun=0, zn_price=0)

    def _changetopology(self, flag_case):
        """Cambia la configurazione topologica della rete.
        flag_case: False -> Chiudi il ramo PCC-node aggiuntivo
                            per avere due linee di connessione
                            con la rete esterna
        flag_case: True -> Chiudi il ramo PCC-node aggiuntivo
                            per avere due linee di connessione
                            con la rete esterna e seziona
                             il mercato in due zone di mercato.
                             Apri linea intermedia."""
        network_mod = cp.deepcopy(self.net)
        intermediate_line = list()
        if flag_case:
            # Caso di contingenza con intersezioni del mercato
            # Si chiude il ramo di emergenza e si apre il ramo intermedio di rete, creando 2 aree
            intermediate_line.append(round(len(network_mod.line) / 2))
            network_mod.line.in_service = True
            for i in intermediate_line:
                network_mod.line.in_service[i] = False
        else:
            # Caso di contingenza senza intersezioni del mercato
            # Si chiude solo il ramo di emergenza
            intermediate_line.append(0)
            for i in range(len(network_mod.line)):
                network_mod.line.in_service[i] = True

        return network_mod, intermediate_line

    def _splitbook(self, split_branch):
        listZNbook = [{'buyer': pd.DataFrame(columns=self.col),
                       'seller': pd.DataFrame(columns=self.col)}
                      for k in range(len(split_branch) + 1)]

        for k in range(len(split_branch)):
            for _idx, _bid in self.book['buyer'].iterrows():
                if _bid.node < split_branch[0]:
                    listZNbook[k]['buyer'] = pd.concat([listZNbook[k]['buyer'], pd.DataFrame(
                        [['Node'+str(_bid.node), _bid.address, _bid.node, _bid.price, _bid.amount]],
                        columns=self.col)]).reset_index(drop=True)
                elif _bid.node >= split_branch[0]:
                    listZNbook[k + 1]['buyer'] = pd.concat([listZNbook[k + 1]['buyer'], pd.DataFrame(
                        [['Node'+str(_bid.node), _bid.address, _bid.node, _bid.price, _bid.amount]],
                        columns=self.col)]).reset_index(drop=True)

            for _idx, _ask in self.book['seller'].iterrows():
                if _ask.node < split_branch[k] and _ask.node != 0:
                    listZNbook[k]['seller'] = pd.concat([listZNbook[k]['seller'], pd.DataFrame(
                        [['Node'+str(_ask.node), _ask.address, _ask.node, _ask.price, _ask.amount]],
                        columns=self.col)]).reset_index(drop=True)
                elif _ask.node >= split_branch[k] and _ask.node != 0.0:
                    listZNbook[k + 1]['seller'] = pd.concat([listZNbook[k + 1]['seller'], pd.DataFrame(
                        [['Node'+str(_ask.node), _ask.address, _ask.node, _ask.price, _ask.amount]],
                        columns=self.col)]).reset_index(drop=True)
                elif _ask.node == 0.0:
                    listZNbook[k]['seller'] = pd.concat([listZNbook[k]['seller'], pd.DataFrame(
                        [['Node'+str(_ask.node), _ask.address, _ask.node, _ask.price, _ask.amount]],
                        columns=self.col)]).reset_index(drop=True)
                    listZNbook[k + 1]['seller'] = pd.concat([listZNbook[k + 1]['seller'], pd.DataFrame(
                        [['Node'+str(_ask.node), _ask.address, _ask.node, _ask.price, _ask.amount]],
                        columns=self.col)]).reset_index(drop=True)

        return listZNbook

    def _deftable(self, listBook, market_p, market_q):
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
                idx += 1

            else:
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

                # Cambia l'ultimo buyer amount
                extramarg_book['buyer'].amount[0] = diff_energyb_ef
                # Cambia l'ultimo seller amount
                extramarg_book['seller'].amount[0] = diff_energys_ef

                # Elimina gli elementi che sono nulli nel campo "amount"
                extramarg_book['buyer'].drop(
                    index=list(extramarg_book['buyer'][extramarg_book['buyer'].amount <= 10e-3].index), inplace=True)
                extramarg_book['seller'].drop(
                    index=list(extramarg_book['seller'][extramarg_book['seller'].amount <= 10e-3].index), inplace=True)

                zn_table[idx] = {'infra-marginal': inframarg_book, 'extra-marginal': extramarg_book}
                idx += 1

        return zn_table

    def _modbus(self, bus_data, congestion):
        """Modifica la configurazione topologica della rete quando ci
        sono congestioni nella rete e restituisci la lista delle zone di mercato."""

        if self.book['seller'].empty or self.book['buyer'].empty:
            # In questo caso non ci sono abbastanza seller o buyer
            # quindi sono tutti definiti come utenti extra-marginali
            # Tutte le offerte entrano ma pagano al prezzo feed-in-tariff o net-price
            listBook = [self.book]

            # Cambiamo topologia di rete per risolvere contingenze
            if congestion:
                # Cambiamo topologia di rete per risolvere contingenze
                net_pp, inter_line = self._changetopology(False)
                # Modifica la rete nella classe che esegue il Power Flow
                self.class_pf.network_pp = net_pp

                # ----Valutiamo rispetto dei vincoli nel caso la topologia di rete sia diversa----
                check_cons_mod = self.class_pf.runPF(bus_data)

                # Set network to the original one
                self.class_pf.network_pp = cp.deepcopy(self.class_pf.network_pp_init)

                if not check_cons_mod:
                    print('Constraint violations after the market split.')

        else:
            # In questo caso ci sono sia seller che buyer
            # quindi definiamo che entra nel mercato e chi no
            # - chi entra nel mercato: utenti infra-marginali;
            # - chi non entra nel mercato: utenti extra-marginali.
            if congestion:
                # Cambiamo topologia di rete per risolvere contingenze
                net_pp, inter_line = self._changetopology(True)

                # Modifica la rete nella classe che esegue il Power Flow
                self.class_pf.network_pp = net_pp

                # Creiamo lista di book per ogni zona di mercato
                listBook = self._splitbook(inter_line)

                # ----Valutiamo rispetto dei vincoli nel caso la topologia di rete sia diversa----
                check_cons_mod = self.class_pf.runPF(bus_data)

                # Set network to the original one
                self.class_pf.network_pp = cp.deepcopy(self.class_pf.network_pp_init)

                if not check_cons_mod:
                    print('Constraint violations after the market split.')

            else:
                # Creiamo lista di book per una singola zona di mercato
                # La lista sarà lunga un elemento
                listBook = [self.book]

        return listBook

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

        D = self._sumordbook(Pdemand)
        S = self._sumordbook(Pgeneration)

        supply = np.array(S)
        demand = np.array(D)
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
        if price_dem[0] > price_gen[0]:
            # Caso in cui ci può essere intersezione del mercato , anche poca generazione.
            # Nel secondo caso essendo la domanda elastica allora esiste comunque un intersezione
            mrk_q, mrk_p = self._findintrsc2(np.array(Pgeneration), np.array(Pdemand), np.array(cost_g), np.array(cost_d))
            x = np.array([mrk_q])
            y = np.array([mrk_p])

        elif price_dem[0] < price_gen[0]:
            if demand[-1] > supply[-1]:
                # --------Troppa generazione a prezzi elevati--------
                # *** Il prezzo zonale è fissato al prezzo dell'ultimo venditore
                y = np.array([ledger['seller'].price[len(ledger['seller']) - 1]])
                # *** La domanda è pari a tutta la quantità venduta dai venditori
                x = np.array([sum(ledger['seller'].amount)])

            elif demand[-1] < supply[-1]:
                # ---------Poca generazione a prezzi elevati---------
                # *** Il prezzo zonale è fissato al prezzo più basso dei compratori
                y = np.array([ledger['buyer'].price[len(ledger['buyer']) - 1]])
                # *** La domanda è pari a tutta la richiesta dei compratori
                x = np.array([sum(ledger['buyer'].amount)])

        return x, y

    def _findintrsc(self, supply, demand, supply_c, demand_c):
        """Nel caso in cui non ci fosse intersezione delle curve
         ma il costo della domanda e superiore all'offerta
         allora cerca la soluzione usando questa funzione."""
        market_q = 0
        market_p = 0
        max_q = supply[-1]
        max_p = supply_c[-1]
        iter = len(demand)

        for i in range(iter):
            if demand_c[i] >= max_p:
                market_q += demand[i]
                market_p = max_p
                if market_q > max_q:
                    # Valuta la quantità che effettivamente riesce ad entrare nel mercato
                    diff_q = demand[i] - (market_q - max_q)
                    # Sottrai la quantità aggiunta precedentemente
                    market_q -= demand[i]
                    # Somma la quantità che entra nel mercato
                    market_q += diff_q
            elif demand_c[i] < max_p:
                break

        return market_q, market_p

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
                        _clear_t=time.time() - self.list_time[_user[1].address])

        elif flag == 1:
            # ---Trasferiamo il contante da SO a SELLER---
            for _user in book['seller'].iterrows():
                if _user[1].address != self.list_p[self.k_addrs[0]].add:
                    self.list_p[_user[1].address].transfer(self.sellGrid * _user[1].amount, False)
                    self.list_p[self.k_addrs[0]].transfer(self.sellGrid * _user[1].amount, True)
                    # Salviamo i contratti
                    self._insertContract(
                        _adrsS=self.k_addrs[0],
                        _adrsB=_user[1].address,
                        _price_kWh=self.sellGrid,
                        _bidPrice=_user[1].price,
                        _cost=-self.sellGrid * _user[1].amount,
                        _amnt=-_user[1].amount,
                        _iter=_iter,
                        _clear_t=time.time() - self.list_time[_user[1].address])

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
                        _clear_t=time.time() - self.list_time[_buyer[1].address])

            for _seller in book['seller'].iterrows():
                if _seller[1].address != self.list_p[self.k_addrs[0]].add:
                    self.list_p[_seller[1].address].transfer(zn_price * _seller[1].amount, False)
                    # Salviamo i contratti
                    self._insertContract(
                        _adrsS=self.k_addrs[0],
                        _adrsB=_seller[1].address,
                        _price_kWh=zn_price,
                        _bidPrice=_seller[1].price,
                        _cost=-zn_price * _seller[1].amount,
                        _amnt=-_seller[1].amount,
                        _iter=_iter,
                        _clear_t=time.time() - self.list_time[_seller[1].address])

    def _insertContract(self, _adrsS, _adrsB, _price_kWh, _bidPrice, _cost, _amnt, _iter, _clear_t):
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

        self.contracts[_iter].append(_cc)

    def set_list(self):
        list_c = {'ID': list(),
                  'adrsB': list(),
                  'adrsS': list(),
                  'cost': list(),
                  'amount': list(),
                  'price [euro/kWh]': list(),
                  'price bid': list(),
                  'interval': list(),
                  'clear_time': list()}

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

        return list_c


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


if __name__ == "__main__":
    # Set fixed SEED
    np.random.seed(0)

    # File per salvataggio - Double Auction market (Centralised)
    filename_DA = 'Results\centralmarket_v2.xlsx'

    # Load network from files
    net = rnet.Net('Networks\LV_16nodi.dat')

    # Create and extract PandaPower network from files
    pp_network = ppnet.PPnet(net).emptyNet

    # Create class for running personalize power flow
    c_pf = rpf.pf(pp_network, net)

    # Prezzo di vendita alla rete
    # 25 EURO/MWh (0.025 EURO/kWh)
    sellGrid = 0.025
    # Prezzo di acquisto dalla rete
    # 400 EURO/MWh (0.4 EURO/kWh)
    buyGrid = 0.4

    m = DAmarket(c_pf, pp_network, buyGrid, sellGrid, Contract())

    # --------------------Mercato------------------
    for t in range(c_pf.time):
        print(t)

        # ------Set previous SoC and Profiles------
        bus_data = c_pf.evalsoc(t)

        # -----------Set Offer and Sort------------
        m.marketoffers(bus_data)

        # ----------------Matching-----------------
        m.matching(t, bus_data)

        # Save data
        c_pf.savevar(t)

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

    eval_class = ef.eval(m.contracts, buyGrid, sellGrid, m.list_p, c_pf)
    eval_class.evalSW()
    eval_class.evalCQR()
    eval_class.writexlsx(filename=filename_DA, sheet_name='Comparison SW', data=eval_class.SW)
    eval_class.writexlsx(filename=filename_DA, sheet_name='Comparison DW', data=eval_class.DW)
    eval_class.writexlsx(filename=filename_DA, sheet_name='Comparison CQR', data=eval_class.CQR)
