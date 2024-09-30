from Networks import readNet as rnet
from Networks import setPPnet as ppnet
from Networks import runpf as rpf
import flex_market as flex
from eth_account import Account
import secrets
import numpy as np
import pandas as pd
import copy as cp
import eval_file as ef
from statistics import mean


class PCDAmarket():
    def __init__(self, sellGrid, buyGrid, network, class_c, class_p, class_bck, neg_time):
        self.sellGrid = sellGrid
        self.buyGrid = buyGrid
        self.net = cp.deepcopy(network)
        self.contract_class = cp.deepcopy(class_c)
        self.participant_class = cp.deepcopy(class_p)
        self.bck_class = cp.deepcopy(class_bck)
        self.nuser = self.net.bus
        self.Participant = dict()
        self.book = dict()
        self.orderBook = dict()
        self.Contract = dict()
        self.list_time = dict()
        self.bck_time = dict()
        self.col = ['ID', 'address', 'node', 'price', 'amount']
        self.negotiation_t = neg_time
        self.master = None
        self._setparticipants()

    def _setparticipants(self):
        """Crea lista dei partecipanti, compreso il System Operator (o master)"""
        for _nu in self.nuser.iterrows():
            p = cp.deepcopy(self.participant_class)
            addrs_p, prvt_key_p = p.setAddr()
            p.add = addrs_p
            p.prvtkey = prvt_key_p
            p.node = float(_nu[1].name)
            if float(_nu[1].name) == 0:
                p.balance = 1e5
                self.master = p
            else:
                p.balance = 1e3
                self.Participant[addrs_p] = p

    def modParticipants(self, _data):
        self.Participant = _data

    def marketoffers(self, _iter, bus_data):
        """Create offers and update book on the market"""
        adrs_so = self.master.add
        df_b = list()
        df_s = list()

        # Per ogni iterazione crea un elemento per i seguenti oggetti
        self.book[_iter] = dict()
        self.orderBook[_iter] = dict()
        self.Contract[_iter] = list()

        # Il mercato si apre
        mu = (self.buyGrid - self.sellGrid) / 2
        sigma = (self.buyGrid - mu) / 3

        rand_list = sorted(list(self.Participant.values()), key=lambda k: np.random.random())
        for _entity in rand_list:
            if _entity.add != adrs_so:
                # Attendiamo qualche istante random per caricare la nuova offerta
                #time.sleep(np.random.uniform(low=0.5, high=2.2, size=1))

                # Offerta in PREZZO
                # "[0]" perché altrimenti estrae un vettore di 1 elemento
                off_price = abs(_entity.offer(mu, sigma, 1)[0])

                # Offerta in QUNATITA'
                # Consideriamo ogni peer come se fosse una singola entità.
                # Quindi vuol dire che l'offerta/richiesta di energia sul mercato sarà pari
                # alla differenza tra generazione e consumo.
                off_amount = round(bus_data.net_p_mw[_entity.node - 1], 7) * 1e3
                if off_amount > 0 and off_amount != 0:
                    df_b.append(['Node' + str(_entity.node), _entity.add, _entity.node, off_price, off_amount])
                elif off_amount < 0 and off_amount != 0:
                    df_s.append(['Node' + str(_entity.node), _entity.add, _entity.node, off_price, -off_amount])

                # Inseriamo il tempo iniziale di piazzamento offerte nella lista dei tempi
                self.list_time[_entity.add] = self.bck_class.blockTime(2)
                self.bck_time[_entity.add] = 0

        # Il mercato si chiude
        self.book[_iter]['buyer'] = pd.DataFrame(df_b, columns=self.col)
        self.book[_iter]['seller'] = pd.DataFrame(df_s, columns=self.col)

    def cda(self, _iter):
        """Start the matching of the Pseudo Continuous Double Auction"""
        # Order the book
        self.orderBook[_iter]['buyer'] = self.book[_iter]['buyer'].sort_values('price', ascending=False, ignore_index=True)
        self.orderBook[_iter]['seller'] = self.book[_iter]['seller'].sort_values('price', ascending=True, ignore_index=True)

        _bb, _bs = self._getlenbs(_iter)

        # Estraggo il tempo impiegato dalla blockchain per eseguire il matching
        # NOTA: Non considerimo i sellers perché il matching viene fatto per ognuno di loro a coppie
        #       quindi non ha senso considerare la somma dei due
        n_buy = len(self.orderBook[_iter]['buyer'])
        bck_time = n_buy * self.bck_class.blockTime(3)

        if _bb and _bs:
            # Buyers & Sellers
            idx = 0
            _check = False
            while not _check:
                idx, _check = self._matchbs(_iter, idx, bck_time)

        elif not _bb and _bs:
            # only Sellers
            idx = 0
            _check = False
            while not _check:
                idx, _check = self._onlybs(_iter, idx, bck_time, False)

        elif _bb and not _bs:
            # only Buyers
            idx = 0
            _check = False
            while not _check:
                idx, _check = self._onlybs(_iter, idx, bck_time, True)

        return True

    def _matchbs(self, _iter, _idx, _bckT):
        """Funzione in cui ci siano sia buyer che seller."""
        itB = len(self.orderBook[_iter]['buyer'])

        if _idx < itB:
            osBid, check_osB, idxSlr = self._getosb(_iter)
            prcSeller = osBid.price
            amntSeller = osBid.amount
            adrsSeller = osBid.address

            prcBuyer = self.orderBook[_iter]['buyer'].price[_idx]
            amntBuyer = self.orderBook[_iter]['buyer'].amount[_idx]
            adrsBuyer = self.orderBook[_iter]['buyer'].address[_idx]

            if check_osB:
                if prcSeller <= prcBuyer:
                    # Definisci il prezzo di acquisto e vendita del contratto
                    contract_price = (self.orderBook[_iter]['buyer'].price[_idx] + self.orderBook[_iter]['seller'].price[idxSlr]) / 2

                    if amntSeller > amntBuyer:
                        # Riduciamo la quantità di energia in vendita del seller
                        self.orderBook[_iter]['seller'].amount[idxSlr] -= amntBuyer
                        # Mettiamo a zero la quantità di energia richiesta del buyer, perché acquistata tutta
                        self.orderBook[_iter]['buyer'].amount[_idx] = 0

                        # Riduci il bilancio del buyer
                        _money2transf = contract_price * amntSeller
                        self.Participant[adrsBuyer].transfer(_money2transf, True)
                        # Aumenta il bilancio del seller
                        self.Participant[adrsSeller].transfer(_money2transf, False)

                        # Insert Contract into class
                        self.insertContract(_price=_money2transf,
                                            _price_kWh=contract_price,
                                            _bidpriceB=self.orderBook[_iter]['buyer'].price[_idx],
                                            _bidpriceS=self.orderBook[_iter]['seller'].price[idxSlr],
                                            _amnt=amntBuyer,
                                            _adrsB=adrsBuyer,
                                            _adrsS=adrsSeller,
                                            _t=_iter,
                                            _clearT=self.list_time[self.orderBook[_iter]['buyer'].address[_idx]] + self.negotiation_t + _bckT,
                                            _totflexCost=0,
                                            _flx_prcS=0,
                                            _flx_prcB=0,
                                            _flxUS=0,
                                            _flxDS=0,
                                            _flxUB=0,
                                            _flxDB=0,
                                            _flexU_slack=0,
                                            _flexD_slack=0)

                        # L'indice avanza perché il buyer è stato soddisfatto
                        _idx += 1

                    else:
                        # Mettiamo a zero la quantità di energia in vendita del seller, perché venduta tutta
                        self.orderBook[_iter]['seller'].amount[idxSlr] = 0
                        # Riduciamo la quantità di energia da acquistare del buyer
                        self.orderBook[_iter]['buyer'].amount[_idx] -= amntSeller

                        # Riduci il bilancio del buyer
                        _money2transf = contract_price * amntBuyer
                        self.Participant[adrsBuyer].transfer(_money2transf, True)
                        # Aumenta il bilancio del seller
                        self.Participant[adrsSeller].transfer(_money2transf, False)

                        # Insert Contract into class
                        self.insertContract(_price=_money2transf,
                                            _price_kWh=contract_price,
                                            _bidpriceS=self.orderBook[_iter]['seller'].price[idxSlr],
                                            _bidpriceB=self.orderBook[_iter]['buyer'].price[_idx],
                                            _amnt=amntSeller,
                                            _adrsB=adrsBuyer,
                                            _adrsS=adrsSeller,
                                            _t=_iter,
                                            _clearT=self.list_time[self.orderBook[_iter]['seller'].address[idxSlr]] + self.negotiation_t + _bckT,
                                            _totflexCost=0,
                                            _flx_prcS=0,
                                            _flx_prcB=0,
                                            _flxUS=0,
                                            _flxDS=0,
                                            _flxUB=0,
                                            _flxDB=0,
                                            _flexU_slack=0,
                                            _flexD_slack=0)

                else:
                    # from Grid - Buyer

                    # Riduci il bilancio del buyer
                    _money2transf = self.buyGrid * amntBuyer
                    self.Participant[adrsBuyer].transfer(_money2transf, True)
                    # Aumenta il bilancio del seller
                    self.master.transfer(_money2transf, False)

                    # Insert Contract into class
                    self.insertContract(_price=_money2transf,
                                        _price_kWh=self.buyGrid,
                                        _bidpriceB=self.orderBook[_iter]['buyer'].price[_idx],
                                        _bidpriceS=0,
                                        _amnt=amntBuyer,
                                        _adrsB=adrsBuyer,
                                        _adrsS=self.master.add,
                                        _t=_iter,
                                        _clearT=self.list_time[adrsBuyer] + self.negotiation_t + _bckT,
                                        _totflexCost=0,
                                        _flx_prcS=0,
                                        _flx_prcB=0,
                                        _flxUS=0,
                                        _flxDS=0,
                                        _flxUB=0,
                                        _flxDB=0,
                                        _flexU_slack=0,
                                        _flexD_slack=0)

                    # Mettiamo a zero la quantità di energia richiesta del buyer, perché acquistata tutta
                    self.orderBook[_iter]['buyer'].amount[_idx] = 0

                    # L'indice avanza perché il buyer è stato soddisfatto
                    _idx += 1

            else:
                # from Grid - Buyer

                # Riduci il bilancio del buyer
                _money2transf = self.buyGrid * amntBuyer
                self.Participant[adrsBuyer].transfer(_money2transf, True)
                # Aumenta il bilancio del seller
                self.master.transfer(_money2transf, False)

                # Insert Contract into class
                self.insertContract(_price=_money2transf,
                                    _price_kWh=self.buyGrid,
                                    _bidpriceB=self.orderBook[_iter]['buyer'].price[_idx],
                                    _bidpriceS=0,
                                    _amnt=amntBuyer,
                                    _adrsB=adrsBuyer,
                                    _adrsS=self.master.add,
                                    _t=_iter,
                                    _clearT=self.list_time[adrsBuyer] + self.negotiation_t + _bckT,
                                    _totflexCost=0,
                                    _flx_prcS=0,
                                    _flx_prcB=0,
                                    _flxUS=0,
                                    _flxDS=0,
                                    _flxUB=0,
                                    _flxDB=0,
                                    _flexU_slack=0,
                                    _flexD_slack=0)

                # Mettiamo a zero la quantità di energia richiesta del buyer, perché acquistata tutta
                self.orderBook[_iter]['buyer'].amount[_idx] = 0

                # L'indice avanza perché il buyer è stato soddisfatto
                _idx += 1

        else:
            # from Grid - Seller
            # Vuol dire che siamo arrivati ai sellers che non hanno ancora venduto
            # try:
            idxS = [idx for idx, row in self.orderBook[_iter]['seller'].iterrows() if row.amount != 0]
            try:
                indexS = idxS[0]  # idxS[-1] + 1
            except IndexError:
                indexS = 0

            # Riduci il bilancio del buyer
            _money2transf = self.sellGrid * self.orderBook[_iter]['seller'].amount[indexS]
            self.master.transfer(_money2transf, True)
            # Aumenta il bilancio del seller
            self.Participant[self.orderBook[_iter]['seller'].address[indexS]].transfer(_money2transf, False)

            # Insert Contract into class
            self.insertContract(_price=_money2transf,
                                _price_kWh=self.sellGrid,
                                _bidpriceS=self.orderBook[_iter]['seller'].price[indexS],
                                _bidpriceB=0,
                                _amnt=self.orderBook[_iter]['seller'].amount[indexS],
                                _adrsB=self.master.add,
                                _adrsS=self.orderBook[_iter]['seller'].address[indexS],
                                _t=_iter,
                                _clearT=self.list_time[self.orderBook[_iter]['seller'].address[indexS]] + self.negotiation_t + _bckT,
                                _totflexCost=0,
                                _flx_prcS=0,
                                _flx_prcB=0,
                                _flxUS=0,
                                _flxDS=0,
                                _flxUB=0,
                                _flxDB=0,
                                _flexU_slack=0,
                                _flexD_slack=0)

            # Mettiamo a zero la quantità di energia venduta dal seller, perché venduta tutta
            self.orderBook[_iter]['seller'].amount[indexS] = 0

            # L'indice avanza perché il buyer è stato soddisfatto
            _idx += 1
            # except:
            #     print(' ')

        _check = self._checkbook(_iter)

        return _idx, _check

    def _onlybs(self, _iter, _i, _bckT, _bb):
        """Funzione per soli casi in cui non ci siano contemporaneamente sia buyer che seller; ma solo casi in cui
        ci siano solo buyer o seller"""
        if _bb:
            # Definisce il costo totale
            _money2transf = self.buyGrid * self.orderBook[_iter]['buyer'].amount[_i]

            # Transfer money of participants
            self.Participant[self.orderBook[_iter]['buyer'].address[_i]].transfer(_money2transf, True)
            self.master.transfer(_money2transf, False)

            # Insert Contract into class
            self.insertContract(_price=_money2transf,
                                _price_kWh=self.buyGrid,
                                _bidpriceB=self.orderBook[_iter]['buyer'].price[_i],
                                _bidpriceS=0,
                                _amnt=self.orderBook[_iter]['buyer'].amount[_i],
                                _adrsB=self.orderBook[_iter]['buyer'].address[_i],
                                _adrsS=self.master.add,
                                _t=_iter,
                                _clearT=self.list_time[self.orderBook[_iter]['buyer'].address[_i]] + self.negotiation_t + _bckT,
                                _totflexCost=0,
                                _flx_prcS=0,
                                _flx_prcB=0,
                                _flxUS=0,
                                _flxDS=0,
                                _flxUB=0,
                                _flxDB=0,
                                _flexU_slack=0,
                                _flexD_slack=0)

            # Mettiamo a zero la quantità di energia richiesta del buyer, perché acquistata tutta dal SO
            self.orderBook[_iter]['buyer'].amount[_i] = 0

        else:
            # Definisce il costo totale
            _money2transf = self.sellGrid * self.orderBook[_iter]['seller'].amount[_i]

            # Transfer money of participants
            self.master.transfer(_money2transf, True)
            self.Participant[self.orderBook[_iter]['seller'].address[_i]].transfer(_money2transf, False)

            # Insert Contract into class
            self.insertContract(_price=_money2transf,
                                _price_kWh=self.sellGrid,
                                _bidpriceS=self.orderBook[_iter]['seller'].price[_i],
                                _bidpriceB=0,
                                _amnt=self.orderBook[_iter]['seller'].amount[_i],
                                _adrsB=self.master.add,
                                _adrsS=self.orderBook[_iter]['seller'].address[_i],
                                _t=_iter,
                                _clearT=self.list_time[self.orderBook[_iter]['seller'].address[_i]] + self.negotiation_t + _bckT,
                                _totflexCost=0,
                                _flx_prcS=0,
                                _flx_prcB=0,
                                _flxUS=0,
                                _flxDS=0,
                                _flxUB=0,
                                _flxDB=0,
                                _flexU_slack=0,
                                _flexD_slack=0)

            # Mettiamo a zero la quantità di energia venduta dal seller, perché venduta tutta al SO
            self.orderBook[_iter]['seller'].amount[_i] = 0

        _i += 1
        _check = self._checkbook(_iter)

        return _i, _check

    def _getlenbs(self, _iter):
        """Restituisci i vettori dell'order book per i buyer e per i seller.
            * 1st return: True if length of buyer greater of zero
            * 2cnd return: True if length of seller greater of zero"""
        if len(self.orderBook[_iter]['buyer']) > 0:
            _bb = True
        else:
            _bb = False

        if len(self.orderBook[_iter]['seller']) > 0:
            _sb = True
        else:
            _sb = False

        return _bb, _sb

    def _getosb(self, _iter):
        lenS = len(self.orderBook[_iter]['seller'])

        check_osB = False
        _index = 0
        _val = 0
        osBid = pd.DataFrame({'address': 0, 'price': 0, 'amount': 0}, index=[0])
        while _index < lenS:
            if self.orderBook[_iter]['seller'].amount[_index] == 0:
                _index += 1
            else:
                check_osB = True
                osBid = self.orderBook[_iter]['seller'].iloc[_index]
                val = _index
                return osBid, check_osB, val

        return osBid, check_osB, _val

    def _checkbook(self, _iter):
        """Questa funzione verifica se ci sono utenti che devono ancora vendere.
         Nel caso ci fossero ancora quantità di energia da vendere e/o comprare restituisce False,
         altrimenti restituisce True."""
        _ch = list()

        for _idx, _row in self.orderBook[_iter]['buyer'].iterrows():
            if _row.amount == 0:
                _ch.append(True)
            else:
                _ch.append(False)

        for _idx, _row in self.orderBook[_iter]['seller'].iterrows():
            if _row.amount == 0:
                _ch.append(True)
            else:
                _ch.append(False)

        _ch = all(_ch)

        return _ch

    def insertContract(self, _price, _price_kWh, _bidpriceS,
                            _bidpriceB, _amnt, _adrsB, _adrsS,
                            _t, _clearT, _totflexCost, _flx_prcS,
                            _flx_prcB, _flxUS, _flxDS, _flxUB, _flxDB,
                            _flexU_slack, _flexD_slack):
        """Insert Contract into class"""
        # Create a copy of the contract class
        _cc = cp.deepcopy(self.contract_class)

        _cc.price = _price
        _cc.price_kWh = _price_kWh
        _cc.bid_priceS = _bidpriceS
        _cc.bid_priceB = _bidpriceB
        _cc.amount = _amnt
        _cc.add_buyer = _adrsB
        _cc.add_seller = _adrsS
        _cc.interval = _t
        _cc.clear_time = _clearT
        _cc.total_flexCost = _totflexCost
        _cc.flex_priceSeller = _flx_prcS
        _cc.flex_priceBuyer = _flx_prcB
        _cc.flex_UprovideS = _flxUS
        _cc.flex_DprovideS = _flxDS
        _cc.flex_UprovideB = _flxUB
        _cc.flex_DprovideB = _flxDB
        _cc.flexU_slack = _flexU_slack
        _cc.flexD_slack = _flexD_slack
        self.Contract[_t].append(_cc)

    def includeflexcost(self, _t, _vFlex, _vSlack, _Summary, _fsp):
        """Includi i dati del servizio di flessibilitò nei contratti."""
        tot_kWh = sum([i.amount for i in self.Contract[_t]])
        user_list = list(self.Participant.keys())

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
        for _i in range(len(self.Participant)):
            flex_upL = _vFlex[flx_ul]['Node' + str(_i + 1)]
            flex_upG = _vFlex[flx_ug]['Node' + str(_i + 1)]
            flex_dwL = _vFlex[flx_dl]['Node' + str(_i + 1)]
            flex_dwG = _vFlex[flx_dg]['Node' + str(_i + 1)]
            if (self.Participant[user_list[_i]].node - 1) in list(_fsp)[0]:
                # Se l'utente si trova tra i partecipanti che hanno offerto nel mercato allora inserisci la slack
                flx_p[user_list[_i]] = [flex_upL, flex_upG, flex_dwL, flex_dwG, slack_up, slack_dw]
            else:
                # Se l'utente non si trovasse tra i partecipanti che hanno offerto nel mercato
                # allora vuol dire che non vuole offrire flessibilità quindi non caricare slack
                flx_p[user_list[_i]] = [flex_upL, flex_upG, flex_dwL, flex_dwG, 0, 0]

        # Modifica i dati dei contratti per includere i costi del servizio di flessibilità
        for _contr in range(len(self.Contract[_t])):
            _cc = self.Contract[_t][_contr]
            buyer_adrs = _cc.add_buyer
            seller_adrs = _cc.add_seller

            _mflex2transf = 0
            if buyer_adrs != self.master.add and seller_adrs != self.master.add:
                # Se sia il Buyer che il Seller non sono il SO allora entrambi partecipano a creare una contingenza.
                # Pertanto dividiamo per 2.
                # Pertanto saranno caricati di una tassa per la provvigione della flessibilità necessaria a risolvere la
                # contingenza che anche loro hanno contribuito a creare.
                _mflex2transf = _totFlexCost * ((_cc.amount / tot_kWh) / 2)

                # Riduciamo la quantità di energia consumata nel contratto di una quota pari alla slack_up
                _cc.amount -= flx_p[buyer_adrs][4]
                # Aumentiamo la quantità di energia consumata nel contratto di una quota pari alla slack_down
                _cc.amount += flx_p[buyer_adrs][5]

            elif buyer_adrs != self.master.add and seller_adrs == self.master.add:
                # Solo il Buyer partecipa a creare una contingenza.
                # Pertanto sarà caricato di una tassa per la provvigione della flessibilità solo il Buyer.
                _mflex2transf = _totFlexCost * (_cc.amount / tot_kWh)

                # Riduciamo la quantità di energia consumata nel contratto di una quota pari alla slack_up
                _cc.amount -= flx_p[buyer_adrs][4]
                # Aumentiamo la quantità di energia consumata nel contratto di una quota pari alla slack_down
                _cc.amount += flx_p[buyer_adrs][5]

            elif buyer_adrs == self.master.add and seller_adrs != self.master.add:
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
            if buyer_adrs != self.master.add:
                # Il servizio UP di flex è pari alla somma del servizio UP dei carichi più quello dei generatori - BUYER
                up_flxB = flx_p[buyer_adrs][0] + flx_p[buyer_adrs][1]
                # Il servizio DW di flex è pari alla somma del servizio DW dei carichi più quello dei generatori - BUYER
                dw_flxB = flx_p[buyer_adrs][2] + flx_p[buyer_adrs][3]

                # Riduci il bilancio del Buyer
                self.Participant[buyer_adrs].transfer(_mflex2transf, True)

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
            if seller_adrs != self.master.add:
                # Il servizio UP di flex è pari alla somma del servizio UP dei carichi più quello dei generatori - SEL
                up_flxS = flx_p[seller_adrs][0] + flx_p[seller_adrs][1]
                # Il servizio DW di flex è pari alla somma del servizio DW dei carichi più quello dei generatori - SEL
                dw_flxS = flx_p[seller_adrs][2] + flx_p[seller_adrs][3]

                # Riduci il bilancio del Seller
                self.Participant[seller_adrs].transfer(_mflex2transf, True)

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
                  'price bid seller': list(),
                  'price bid buyer': list(),
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

        for _k in self.Contract.keys():
            _idx = 0
            for _value in self.Contract[_k]:
                list_c['ID'].append(_idx)
                list_c['adrsB'].append(_value.add_buyer)
                list_c['adrsS'].append(_value.add_seller)
                list_c['cost'].append(_value.price)
                list_c['amount'].append(_value.amount)
                list_c['price [euro/kWh]'].append(_value.price_kWh)
                list_c['price bid seller'].append(_value.bid_priceS)
                list_c['price bid buyer'].append(_value.bid_priceB)
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
            list_c['price bid seller'].append('-')
            list_c['price bid buyer'].append('-')
            list_c['interval'].append('-')
            list_c['clear_time'].append('-')
            list_c['flex_priceSeller'].append('-')
            list_c['flex_priceBuyer'].append('-')
            list_c['flex_UprovideS'].append('-')
            list_c['flex_DprovideS'].append('-')
            list_c['flex_UprovideB'].append('-')
            list_c['flex_DprovideB'].append('-')
            list_c['flexU_slack'].append('-')
            list_c['flexD_slack'].append('-')
            list_c['total_flex_Cost'].append('-')

        return list_c

    def addTime(self, _iter, _case):
        """Carica i tempi d'interazione con blockchain per il mercato di flessibilità"""
        if _case:
            # Caso Mercato di Flessibilità in cui ogni utente carica la sua offerta
            solution_time = 0

            for _index in self.Participant.keys():
                self.bck_time[_index] += self.bck_class.blockTime(2) + solution_time
        else:
            # Caso Mercato di flessibilità in cui il SO carica la soluzione finale su BCK
            solution_time = self.bck_class.blockTime(2)

            for _index in self.Participant.keys():
                self.bck_time[_index] += self.bck_class.blockTime(2) + solution_time

            for _contr in self.Contract[_iter]:
                try:
                    _contr.clear_time += self.bck_time[_contr.add_buyer]
                except KeyError:
                    _contr.clear_time += self.bck_time[_contr.add_seller]

    def collecttimes(self):
        list_times = list()

        for _k in self.Contract.keys():
            _idx = 0
            list_time_interval = list()
            for _value in self.Contract[_k]:
                list_time_interval.append(_value.clear_time)
            list_times.append(mean(list_time_interval))

        return list_times


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


class Contract():
    def __init__(self):
        self.add_seller = None
        self.add_buyer = None
        self.price_kWh = None
        self.price = None
        self.bid_priceS = None
        self.bid_priceB = None
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


class bck():
    def setAddr(self):
        priv = secrets.token_hex(32)
        private_key = "0x" + priv
        acct = Account.from_key(private_key)
        return acct.address, private_key

    def gasUsage(self, _user, _fcn):
        """Restituisce il gas consumato per ogni azione implementata su blockchain.
        Tutti gli utenti quando usano la piattaforma possono:
        1) registrarsi
        2) caricare offerte
        Il gestore di rete invece dovrà fare il matching chiamando l'opportuna funzione.
        Quando la chiama pagherà una fee che distribuirà agli utenti. Questa fee sarà però automaticamente aggiunta
        come costo aggiuntivo quando si piazza l'offerta. Il gestore quindi potrà:
        1) eseguire il matching
        """
        if _user:
            # Gestore di rete (gas Cost estratto da Remix)
            mu = 920000  # [gas] average gas usage
            sigma = (mu-800000)/3  # [gas] dev std per gas usage
            gasCost = np.random.normal(mu, sigma, 1)
        else:
            # Utenti (gas Cost estratto da Remix)
            if _fcn:
                # _fcn = true | set_issuer
                gasCost = [65799]
            else:
                # _fcn = false | make_offer
                mu = 350000  # [gas] average gas usage
                sigma = (mu-295000)/3  # [gas] dev std per gas usage
                gasCost = np.random.normal(mu, sigma, 1)

        return gasCost[0]

    def blockTime(self, _fncs):
        """Restituisce il tempo per ogni tipo di chiamata alla blockchain.
        Esistono 3 funzioni che possono essere chiamate:
        1) registrazione partecipanti
        2) registrazione offerte degli utenti
        3) matching del gestore di rete
        Per ognuna di queste restituiamo il tempo. Il tempo lo estrarremo da Remix. A questo aggiungiamo un tempo random
        estratto da distribuzione di probabilità."""
        if _fncs == 1:
            # Registrazione partecipanti
            mu = 0.001
            sigma = (mu - 0.0001)/3
            time = np.random.normal(mu, sigma, 1)
        elif _fncs == 2:
            # Registrazione offerte
            mu = 0.55
            sigma = (mu - 0.2)/3
            time = np.random.normal(mu, sigma, 1)
        else:
            # Matching del gestore di rete per un singolo matching (1 buyer - 1 seller)
            mu = 1.6
            sigma = (mu - 0.1)/3
            time = np.random.normal(mu, sigma, 1)

        return time[0]


if __name__ == "__main__":
    # Set fixed SEED
    np.random.seed(0)

    # File per salvataggio - Pseudo Continuous Double Auction market (Distributed)
    filename_PCDA = 'Results\pcda_market_test251122.xlsx'

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

    # Negotiation time [30 minuti
    neg_time = 30 * 60

    m = PCDAmarket(sellGrid, buyGrid, pp_network, Contract(), Participant(), bck(), neg_time)
    # Inseriamo la classe dei partecipanti del CMmarket dentro la classe PCDAmarket
    m.modParticipants(cm.list_p)

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
            m.marketoffers(t, bus_data)

            # ----------------Matching-----------------
            m.cda(t)

            # Run PF
            check_cons = c_pf.runPF(bus_data)

            # Get result of network
            c_pf.savevar(t)
            res_net = c_pf.res_net

            if not check_cons:
                # Inseriamo una copia della rete pandapower (con i risultati del power flow) dentro la classe CMmarket
                cm.net = cp.deepcopy(c_pf.network_pp)

                # Elaborate parameters for optimisation
                nCONG, req_flex = cm.evalnet(t, res_net)

                # Make Offers (only loads can offer flexibility - "for now")
                fsp = cm.makeoffer(res_net, t)

                # Aggiungiamo il tempo di caricare l'offerta di ogni utente
                # nella lista dei tempi blockchain della classe PCDAmarket
                m.addTime(t, _case=True)

                # Optimise
                model_opt, vars = cm.setOptModel(nCONG, req_flex, False)
                v_flex, v_slack, summary = cm.extractOptValue(vars, nCONG)

                # Aggiungiamo il tempo di caricare la soluzione del SO nella lista dei tempi della classe PCDAmarket
                m.addTime(t, _case=False)

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
    #     list_ctimes[_i] = m.collecttimes()
    # c_pf.write_excel(filename=filename_PCDA, sheet_name='Time Eval', data=list_ctimes)

    # Extract list of contracts
    list_cntr = m.set_list()

    # Save list of contracts on Excel
    c_pf.write_excel(filename=filename_PCDA, sheet_name='Market times', data=list_cntr)

    # Save data on DataFrame
    c_pf.savedf()

    # Extract Data
    df_net = c_pf.df_net

    # Save networks results on Excel
    c_pf.write_excel(filename=filename_PCDA, sheet_name='ppeer_kw',         data=df_net['ppeer_df'])
    c_pf.write_excel(filename=filename_PCDA, sheet_name='qpeer_kvar',       data=df_net['qpeer_df'])
    c_pf.write_excel(filename=filename_PCDA, sheet_name='vmpeer',           data=df_net['vmpeer_df'])
    c_pf.write_excel(filename=filename_PCDA, sheet_name='pLoad',            data=df_net['pLoad_df'])
    c_pf.write_excel(filename=filename_PCDA, sheet_name='pGen',             data=df_net['pGen_df'])
    c_pf.write_excel(filename=filename_PCDA, sheet_name='pStore',           data=df_net['pStore_df'])
    c_pf.write_excel(filename=filename_PCDA, sheet_name='pVeicolo',         data=df_net['pVeicolo_df'])
    c_pf.write_excel(filename=filename_PCDA, sheet_name='SoC_storage',      data=df_net['SoC_df'])
    c_pf.write_excel(filename=filename_PCDA, sheet_name='Line Loading',     data=df_net['line_df'])
    c_pf.write_excel(filename=filename_PCDA, sheet_name='Trafo Loading',    data=df_net['trafo_df'])

    # Save Users and addresses on Excel
    c_pf.write_excel(filename=filename_PCDA,
                     sheet_name='User addresses',
                     data={'address': m.Participant.keys(), 'node': [m.Participant[k].node for k in m.Participant.keys()]})

    eval_class = ef.eval(m.Contract, buyGrid, sellGrid, m.Participant, m.master.add, c_pf)
    eval_class.evalSW(True)
    eval_class.evalCQR(True)
    eval_class.writexlsx(filename=filename_PCDA, sheet_name='Comparison SW',        data=eval_class.SW)
    eval_class.writexlsx(filename=filename_PCDA, sheet_name='Comparison DW',        data=eval_class.DW)
    eval_class.writexlsx(filename=filename_PCDA, sheet_name='Comparison CQR',       data=eval_class.CQR)
    eval_class.writexlsx(filename=filename_PCDA, sheet_name='Comparison tot bid',   data=eval_class.tot_bid)
