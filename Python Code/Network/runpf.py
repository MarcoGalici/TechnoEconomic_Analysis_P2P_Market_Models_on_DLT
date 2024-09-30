from Networks import readNet as rnet
from Networks import setPPnet as ppnet
import pandapower as pp
import copy as cp
import pandas as pd
from os.path import exists
import numpy as np
from tkinter.messagebox import showwarning as shw


class pf():
    def __init__(self, netpp, netf90):
        self.network_pp = netpp
        self.network_pp_init = cp.deepcopy(netpp)
        self.network_f90 = netf90
        self.profiles = net.setProfile()[0]
        self.types = net.setProfile()[1]
        self.time = self._definetime()
        self.dt = 24/self.time
        self.res_net = self._defvar()
        self.df_net = dict()
        self.element_df = dict()
        self.res_pf = dict()

    def _definetime(self):
        """Definisce il tempo di ogni intervallo temporale"""
        return len(self.profiles['Gens'][0])

    def _defvar(self):
        """Crea delle variabili vuote utili per salvare le variabili di interesse durante il ciclo di power flow.
        Viene eseguito solo all'inizio del primo ciclo di power flow"""
        prev_soc = []
        SoC = dict()
        p_Veicolo = dict()
        p_Store = dict()
        p_Gen = dict()
        p_Load = dict()
        p_peer = dict()
        q_peer = dict()
        vm_peer = dict()
        line = dict()
        trafo = dict()

        res_net = dict()
        res_net['prev_soc'] = prev_soc
        res_net['SoC'] = SoC
        res_net['p_Veicolo'] = p_Veicolo
        res_net['p_Store'] = p_Store
        res_net['p_Gen'] = p_Gen
        res_net['p_Load'] = p_Load
        res_net['p_peer'] = p_peer
        res_net['q_peer'] = q_peer
        res_net['vm_peer'] = vm_peer
        res_net['line'] = line
        res_net['trafo'] = trafo

        return res_net

    def _setinitsoc(self, _iter, prev_soc):
        """Retrieve Initial State of Charge for peers (only for those who have availability of storage).
        - Facciamo l'ipotesi che l'SOC dei veicoli sia sempre 50% alla prima ora della giornata,
        - Lo stato di carica iniziale sarà estratto da una distribuzione uniforme tra il valore di min_soc e max_soc"""
        d = dict()
        d['name'] = list()
        d['soc_init'] = list()

        for i in list(self.network_pp.storage.index):
            d['name'].append(self.network_pp.storage.at[i, "name"])

            if _iter == 0:
                if 'Storage' in self.network_pp.storage.at[i, "name"]:
                    d['soc_init'].append(
                        self.network_pp.storage.at[i, "soc_percent"] * self.network_pp.storage.at[i, "max_e_mwh"]
                    )
                else:
                    d['soc_init'].append(
                        np.random.uniform(low=0.1, high=0.9, size=1)[0] * self.network_pp.storage.at[i, "max_e_mwh"]
                    )
            else:
                d['soc_init'].append(prev_soc.at[i, "soc_t1"])

        return pd.DataFrame(d)

    def _getProfile(self, _iter, soc_init):
        """Define profiles of Loads, Generators, Storage Systems and Electric Vehicles"""
        loads = self.profiles['Loads']
        gens = self.profiles['Gens']
        ev = self.profiles['EV']
        typeL = self.types['Loads']
        typeG = self.types['Gens']
        typeEV = self.types['EV']

        # LOADS
        load_data = dict()
        load_data['bus'] = list()
        load_data['p_mw'] = list()
        load_data['q_mvar'] = list()
        for i in list(self.network_pp_init.load.index):
            load_data['bus'].append(self.network_pp_init.load.at[i, "bus"])
            load_data['p_mw'].append(self.network_pp_init.load.at[i, "p_mw"] * loads[int(typeL[i]) - 1][_iter])
            load_data['q_mvar'].append(self.network_pp_init.load.at[i, "q_mvar"] * loads[int(typeL[i]) - 1][_iter])

        load_df = pd.DataFrame(load_data)

        # GENERATORS
        gen_data = dict()
        gen_data['bus'] = list()
        gen_data['p_mw'] = list()
        typeG = [k for k in typeG if k != 0]
        for i in list(self.network_pp_init.gen.index):
            gen_data['bus'].append(self.network_pp_init.gen.at[i, "bus"])
            gen_data['p_mw'].append(self.network_pp_init.gen.at[i, "p_mw"] * gens[int(typeG[i]) - 1][_iter])

        gen_df = pd.DataFrame(gen_data)

        # STORAGES & ELECTRIC VEHICLES
        store_data = dict()
        store_data['name'] = list()
        store_data['bus'] = list()
        store_data['soc_t0'] = list()
        store_data['soc_t1'] = list()
        store_data['p_mw'] = list()
        store_data['p_veicolo_mw'] = list()
        for i in list(self.network_pp_init.storage.index):
            # Consumo
            cons = load_df.at[np.where(load_df == self.network_pp_init.storage.bus[i])[0][0], "p_mw"]
            # Produzione
            try:
                prod = gen_df.at[np.where(gen_df == self.network_pp_init.storage.bus[i])[0][0], "p_mw"]
            except IndexError:
                prod = 0.0
            # Delta di produzione (positive = injection / negative = consumption)
            dP = prod - cons
            # Initial State of Charge of the Storage Elements
            isoc = soc_init.at[i, 'soc_init']
            store_data['soc_t0'].append(isoc)
            # Save 'name' and 'bus'
            store_data['name'].append(self.network_pp_init.storage.at[i, "name"])
            store_data['bus'].append(self.network_pp_init.storage.at[i, "bus"])

            if 'Storage' in self.network_pp_init.storage.at[i, "name"]:
                p_stor, fsoc = self._storageprof(i, dP, isoc)
                store_data['soc_t1'].append(fsoc)
                store_data['p_mw'].append(p_stor)
                store_data['p_veicolo_mw'].append(0)
            else:
                p_stor, fsoc, p_veicolo = self._evprof(i, ev, typeEV, isoc, _iter)
                store_data['soc_t1'].append(fsoc)
                store_data['p_mw'].append(p_stor)
                store_data['p_veicolo_mw'].append(p_veicolo)

        store_df = pd.DataFrame(store_data)

        return load_df, gen_df, store_df

    def _storageprof(self, idx, dP, isoc):
        """Define if the battery should charge or discharge according to the production and consumption net profile"""
        soc = 0
        p_stor = 0
        # Capacità nominale della batteria
        cap = self.network_pp_init.storage.at[idx, "max_e_mwh"]
        # Capacità Max
        # Mettiamo 0.9 perché il modello di storage di PandaPower non ha il parametro Capacità Nominale [kWh],
        # quindi usiamo "max_e_mwh" come parametro per mettere la capacità nominale
        cap_max = cap * 0.9
        # Capacità Min
        cap_min = self.network_pp_init.storage.at[idx, "min_e_mwh"]

        # Charge
        if dP > 0:
            # La massima energia di Carica possibile
            E_charge = dP * self.dt

            if isoc + E_charge < cap_max:
                # Posso ancora caricare
                p_stor = E_charge / self.dt
                soc = isoc + E_charge

            elif isoc + E_charge > cap_max:
                # La carica andrebbe oltre la cap_max, uso una carica ridotta
                E_charge_ridotta = (cap_max - isoc) * self.dt
                p_stor = E_charge_ridotta / self.dt
                soc = isoc + E_charge_ridotta

            elif isoc == cap_max:
                # Non posso più Caricare
                p_stor = 0
                soc = cap_max

        # Discharge
        elif dP <= 0:
            # La massima energia di Scarica possibile (segno negativo)
            E_discharge = dP * self.dt

            if isoc + E_discharge > cap_min:
                # Posso ancora scaricare
                p_stor = E_discharge / self.dt
                soc = isoc + E_discharge

            elif (isoc + E_discharge) < cap_min:
                # La scarica andrebbe oltre la cap_min, uso una scarica ridotta
                E_discharge_ridotta = (cap_min - isoc) * self.dt
                p_stor = E_discharge_ridotta / self.dt
                soc = isoc + E_discharge_ridotta

            elif isoc == cap_min:
                # Non posso più Scaricare
                p_stor = 0
                soc = cap_min

        return p_stor, soc

    def _evprof(self, idx, ev, typeEV, isoc, _iter):
        """Define if electric vehicle is supposed to charge or discharge.
        - In case it should charge (vehicle is plugged to the charging station) use the class function _storageprof to set
          profile.
        - In case it should discharge (vehicle unplugged) evaluate distance perfomed, consumption etc.. to define amount
          of energy consumed."""
        p_ev = self.network_pp_init.storage.at[idx, "p_mw"] * ev[int(typeEV[idx]) - 1][_iter]
        battCap = self.network_pp_init.storage.at[idx, "max_e_mwh"]
        min_soc = 0.1 * battCap
        # max_soc = 0.9 * battCap

        if p_ev != 0:
            # VEHICLE PLUGGED
            # State of Charge of the Vehicle
            p_ev, soc = self._storageprof(idx, p_ev, isoc)
            p_veicolo = 0
        else:
            # VEHICLE UNPLUGGED
            # Consumption - extracted randomly
            mu, sigma = 0.2, 0.1
            C = abs(np.random.normal(loc=mu, scale=sigma, size=1)[0]) * 1e-3
            # Distance - extracted randomly
            mu, sigma = 30, 5
            D = np.random.normal(loc=mu, scale=sigma, size=1)[0]
            # Stato di carica
            soc = isoc - D * C
            if soc < min_soc:
                soc = min_soc
            p_ev = 0
            p_veicolo = (soc - isoc) / self.dt

        return p_ev, soc, p_veicolo

    def _setpoint(self, load_df, gen_df, store_df):
        """Set the point of functioning for elements in network PandaPower"""
        bus_data = dict()
        bus_data['bus'] = list()
        bus_data['net_p_mw'] = list()
        bus_data['net_q_mvar'] = list()
        for j in list(self.network_pp_init.bus.index):
            if not 'ExtGrid' in self.network_pp_init.bus.name[j]:
                bus_data['bus'].append(j)
                try:
                    ld_index_p = [load_df.at[np.where(load_df.bus == j)[0][i], "p_mw"] for i in range(len(np.where(load_df.bus == j)[0]))]
                    ld_index_q = [load_df.at[np.where(load_df.bus == j)[0][i], "q_mvar"] for i in range(len(np.where(load_df.bus == j)[0]))]
                except:
                    ld_index_p = []
                    ld_index_q = []
                try:
                    gen_index = [gen_df.at[np.where(gen_df.bus == j)[0][i], "p_mw"] for i in range(len(np.where(gen_df.bus == j)[0]))]
                except:
                    gen_index = []
                try:
                    store_index = [store_df.at[np.where(store_df.bus == j)[0][i], "p_mw"] for i in range(len(np.where(store_df.bus == j)[0]))]
                except:
                    store_index = []

                bus_data['net_p_mw'].append(sum(ld_index_p) + sum(store_index) - sum(gen_index))
                bus_data['net_q_mvar'].append(sum(ld_index_q))

        bus_df = pd.DataFrame(bus_data)

        return bus_df

    def evalsoc(self, _iter):
        """Set SoC of previous state"""
        prev_soc = self.res_net['prev_soc']
        isoc_df = self._setinitsoc(_iter, prev_soc)

        load_df, gen_df, store_df = self._getProfile(_iter, isoc_df)
        prev_soc = store_df.iloc[:, [0, 3]]
        bus_data = self._setpoint(load_df, gen_df, store_df)
        self.res_net['prev_soc'] = prev_soc

        self.element_df['load'] = load_df
        self.element_df['gen'] = gen_df
        self.element_df['store'] = store_df
        return bus_data

    def _adjust(self, data):
        """Set element as load or genereator according to the sign of the net power injected/consumed
        - Inizialmente mettiamo tutti i parametri di produzione e consumo a zero,
        - Successivamente modifichiamo i valori di consumo/produzione (usiamo carichi positivi o negativi)"""
        self.network_pp.load.p_mw = 0
        self.network_pp.load.q_mvar = 0
        self.network_pp.gen.p_mw = 0
        self.network_pp.storage.p_mw = 0

        self.network_pp.load.p_mw = data.net_p_mw
        self.network_pp.load.q_mvar = data.net_q_mvar

    def _check_net(self):
        """This function will check the net contraints meeting on the lines and on nodes"""

        lines_meet_constraints = False
        if self.network_pp.res_line[self.network_pp.res_line["loading_percent"] > 100.0].shape[0] == 0:
            lines_meet_constraints = True

        voltages_meet_constraints = False
        if self.network_pp.res_line.query("vm_from_pu < 0.95 & vm_from_pu > 1.05").shape[0] == 0:
            voltages_meet_constraints = True

        return lines_meet_constraints, voltages_meet_constraints

    def runPF(self, bus_data):
        """Run Power Flow 1 times"""
        self._adjust(bus_data)

        pp.runpp(self.network_pp)

        line_cs, node_cs = self._check_net()

        check_const = True

        if not line_cs:
            print('Warning - Lines')
            check_const = False

        if not node_cs:
            print('Warning - Nodes')
            check_const = False

        self.res_pf['vm'] = self.network_pp.res_bus.vm_pu
        self.res_pf['p_kw'] = self.network_pp.res_bus.p_mw * 1e3
        self.res_pf['q_kvar'] = self.network_pp.res_bus.q_mvar * 1e3
        self.res_pf['line'] = self.network_pp.res_line.loading_percent
        self.res_pf['trafo'] = self.network_pp.res_trafo.loading_percent * 1e2
        return check_const

    def savevar(self, _iter):
        self.res_net['SoC'][_iter] = list(self.res_net['prev_soc'].soc_t1 * 1e3)
        self.res_net['p_Veicolo'][_iter] = list(self.element_df['store'].iloc[:, -1] * 1e3)
        self.res_net['p_Store'][_iter] = list(self.element_df['store'].iloc[:, 4] * 1e3)
        self.res_net['p_Gen'][_iter] = list(self.element_df['gen'].iloc[:, 1] * 1e3)
        self.res_net['p_Load'][_iter] = list(self.element_df['load'].iloc[:, 1] * 1e3)
        self.res_net['p_peer'][_iter] = list(self.res_pf['p_kw'])
        self.res_net['q_peer'][_iter] = list(self.res_pf['q_kvar'])
        self.res_net['vm_peer'][_iter] = list(self.res_pf['vm'])
        self.res_net['line'][_iter] = list(self.res_pf['line'])
        self.res_net['trafo'][_iter] = list(self.res_pf['trafo'])

    def savedf(self):
        SoC_df = pd.DataFrame.from_dict(self.res_net['SoC'], orient='index', columns=list(self.network_pp_init.storage.name))
        pVeicolo_df = pd.DataFrame.from_dict(self.res_net['p_Veicolo'], orient='index', columns=list(self.network_pp_init.storage.name))
        pStore_df = pd.DataFrame.from_dict(self.res_net['p_Store'], orient='index', columns=list(self.network_pp_init.storage.name))
        pGen_df = pd.DataFrame.from_dict(self.res_net['p_Gen'], orient='index', columns=list(self.network_pp_init.gen.bus))
        pLoad_df = pd.DataFrame.from_dict(self.res_net['p_Load'], orient='index', columns=list(self.network_pp_init.load.bus))
        ppeer_df = pd.DataFrame.from_dict(self.res_net['p_peer'], orient='index', columns=list(self.network_pp_init.bus.index))
        qpeer_df = pd.DataFrame.from_dict(self.res_net['q_peer'], orient='index', columns=list(self.network_pp_init.bus.index))
        vmpeer_df = pd.DataFrame.from_dict(self.res_net['vm_peer'], orient='index', columns=list(self.network_pp_init.bus.index))
        line_df = pd.DataFrame.from_dict(self.res_net['line'], orient='index', columns=list(self.network_pp_init.line.index))
        trafo_df = pd.DataFrame.from_dict(self.res_net['trafo'], orient='index', columns=list(self.network_pp_init.trafo.index))

        self.df_net['SoC_df'] = SoC_df
        self.df_net['pVeicolo_df'] = pVeicolo_df
        self.df_net['pStore_df'] = pStore_df
        self.df_net['pGen_df'] = pGen_df
        self.df_net['pLoad_df'] = pLoad_df
        self.df_net['ppeer_df'] = ppeer_df
        self.df_net['qpeer_df'] = qpeer_df
        self.df_net['vmpeer_df'] = vmpeer_df
        self.df_net['line_df'] = line_df
        self.df_net['trafo_df'] = trafo_df

    def write_excel(self, filename, sheet_name, data):
        """Trasforma un dizionario in un dataframe e scrivi i valori dentro un file excel"""

        df1 = pd.DataFrame.from_dict(data)
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


if __name__ == "__main__":
    np.random.seed(0)

    # Load network from files
    net = rnet.Net('LV_16nodi_v4.dat')

    # Create and extract PandaPower network from files
    pp_network = ppnet.PPnet(net).emptyNet

    # Create class for running personalize power flow
    c_pf = pf(pp_network, net)

    # Esegui power flow T volte
    for t in range(c_pf.time):
        # Set SoC of previous state
        bus_data = c_pf.evalsoc(t)

        # Run PF
        check_cons = c_pf.runPF(bus_data)
        if not check_cons:
            print('Time: ', t)

        # Save data
        c_pf.savevar(t)

    # Salva i dati
    c_pf.savedf()

    # Estrai i dati
    df_net = c_pf.df_net