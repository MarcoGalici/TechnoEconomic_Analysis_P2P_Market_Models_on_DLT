from pandapower.pd2ppc import _ppc2ppci
import pandapower.pypower.makePTDF as PTDF
import gurobipy as gp
from gurobipy import GRB
import copy as cp
import numpy as np
import pandas as pd
import math
import matplotlib.pyplot as plt
from Networks import runpf as rpf
from Networks import readNet as rnet
from Networks import setPPnet as ppnet
from eth_account import Account
import secrets


class flexContract():
    pass


class Participant():
    def __int__(self, _node, _balance, _add, _prvt_key):
        self.node = _node
        self.balance = _balance
        self.add = _add
        self.prvtkey = _prvt_key

    def setAddr(self):
        priv = secrets.token_hex(32)
        private_key = "0x" + priv
        acct = Account.from_key(private_key)
        return acct.address, private_key

    def offer(self, _mu, _sigma, _howManyNumbers):
        """Le offerte dei partecipanti avranno come media il valore medio tra il costo di acquisto dell'energia dalla
        rete e il costo di acquisto dalla rete. Infine come std dev assumeranno un valore pari a 1/3 della deviazione
        tra la media ed il valore massimo, che sarà pari al costo di acqusito dalla rete."""
        return np.random.normal(_mu, _sigma, _howManyNumbers)


class CMmarket():
    def __init__(self, pf_net, network, class_p):
        self.pf_net = pf_net
        self.net_init = cp.deepcopy(network)
        self.fsp_class = cp.deepcopy(class_p)
        self.slack = self.net_init.ext_grid.bus
        self.list_p = dict()
        self.smax_lines = np.array(math.sqrt(3) * self.net_init.bus.vn_kv[self.net_init.line.to_bus].reset_index(drop=True) * self.net_init.line.max_i_ka.values, ndmin=2).transpose()
        self.smax_trafos = np.array(self.net_init.trafo.sn_mva.values, ndmin=2).transpose()
        self.max_off = 0.4995  # [euro/kWh] - Dati presi da risultati mercato piattaforma PicloFlex (U.K.)
        self.min_off = 0.1662  # [euro/kWh] - Dati presi da risultati mercato piattaforma PicloFlex (U.K.)
        self.cost_s = 2 * self.max_off
        self.smax_node = None
        self.nFSP = None
        self.net = None
        self.ptdf = None
        self.sens_mat = None
        self.sens_df = None
        self.fspUP_g = None
        self.fspUP_l = None
        self.fspDW_g = None
        self.fspDW_l = None
        self.fspUPc_g = None
        self.fspUPc_l = None
        self.fspDWc_g = None
        self.fspDWc_l = None
        self._setparticipants()
        self._setsmvanode()

    def _setparticipants(self):
        """Crea lista dei partecipanti"""
        for _nu in list(self.net_init.bus.index):
            if _nu not in self.slack:
                p = cp.deepcopy(self.fsp_class)
                p.node = _nu
                addrs_p, prvt_key_p = p.setAddr()
                p.add = addrs_p
                p.prvtkey = prvt_key_p
                p.balance = 1e3
                self.list_p[addrs_p] = p
        self.nFSP = len(self.list_p)

    def _setsmvanode(self):
        smva_gen = np.zeros((len(self.net_init.bus.index.drop(self.slack)), 1))
        smva_load = np.zeros((len(self.net_init.bus.index.drop(self.slack)), 1))

        idx_load = np.asarray(self.net_init.load.bus) - len(self.slack)
        idx_gen = np.asarray(self.net_init.gen.bus) - len(self.slack)

        smva_load[idx_load] = np.array(self.net_init.load.sn_mva, ndmin=2).transpose()
        smva_gen[idx_gen] = np.array(self.net_init.gen.sn_mva, ndmin=2).transpose()

        self.smax_node = smva_load + smva_gen

    def _getptdf(self):
        # Run power flow to obtain ppc and mapping the internal/external indexes of busses
        # After defining _ppc (ppc = net['_ppc']), convert to "pandapower format". To do this use the function "_ppc2ppci"
        # "ppci" is the pandapower format for net
        ppci = _ppc2ppci(self.net['_ppc'], self.net)

        # Extract bus indexes and convert to DataFrame
        bus_map_table = pd.DataFrame(self.net.bus.index.values)

        # Extract PTDF and convert to DataFrame
        ptdf_table = pd.DataFrame(PTDF.makePTDF(ppci['baseMVA'], ppci['bus'], ppci['branch'], self.net.ext_grid.bus.values[0]))

        # Round the data in the DataFrame (that is why the low data is shown as zero)
        PTDF_Test = ptdf_table.round(2)

        sens = self.net.res_line.values[:, 0]
        sens1 = pd.DataFrame(sens).T

        line_sens = [i for i in range(len(sens1.T)) if sens1.values[0, i] < 0]

        for k in line_sens:
            for j in range(len(PTDF_Test.T)):
                PTDF_Test.iloc[k, j] = -1 * PTDF_Test.values[k, j]

        self.ptdf = PTDF_Test

    def _getelements(self, loading, smax, max, min):
        """Return Overloaded/underloaded elements (lines, trafos and nodes)"""
        idx_ol = np.array(np.where(loading > max)[0], ndmin=2).transpose()
        overload = loading[np.where(loading > max)[0]]

        idx_ul = np.array(np.where(loading < min)[0], ndmin=2).transpose()
        underload = loading[np.where(loading < min)[0]]

        smaxs_ol = smax[np.where(loading > max)[0]]
        smaxs_ul = smax[np.where(loading < min)[0]]

        flexibility_up = overload - max
        flexibility_dw = underload - min

        dict_elem = {'idx_ol': idx_ol, 'overload': overload, 'flexUP': flexibility_up, 'MVA_ol': smaxs_ol,
                     'idx_ul': idx_ul, 'undeload': underload, 'flexDW': flexibility_dw, 'MVA_ul': smaxs_ul}

        return dict_elem

    def evalnet(self, _iter, res_net):

        res_lines, res_trafos, res_nodes = res_net['line'][_iter], res_net['trafo'][_iter], res_net['vm_peer'][_iter]
        self._getptdf()

        line_df = np.array(res_lines, ndmin=2).transpose()
        dict_line = self._getelements(line_df, self.smax_lines, 100, 0)

        trafo_df = np.array(res_trafos, ndmin=2).transpose()
        dict_trafo = self._getelements(trafo_df, self.smax_trafos, 100, 0)

        node_df = np.array(res_nodes, ndmin=2).transpose()
        dict_node = self._getelements(node_df, self.smax_node, 1.05, 0.95)

        # DSO needs of flexibility - LINES
        flex_line = dict()
        flex_line['time'] = _iter * np.ones((len(dict_line['idx_ol']), 1))
        flex_line['line_ol'] = dict_line['idx_ol']
        flex_line['overload %'] = dict_line['overload']
        flex_line['flexUP %'] = dict_line['flexUP']
        flex_line['flexUP MVA'] = ((dict_line['flexUP'] * dict_line['MVA_ol']) / 100)
        flex_line['flexUP MW'] = ((dict_line['flexUP'] * dict_line['MVA_ol']) / 100) * self.pf_net
        flex_line['flexUP MVar'] = ((dict_line['flexUP'] * dict_line['MVA_ol']) / 100) * math.sin(math.acos(self.pf_net))
        flex_line['line_ul'] = dict_line['idx_ul']
        flex_line['underload %'] = dict_line['undeload']
        flex_line['flexDW %'] = dict_line['flexDW']
        flex_line['flexDW MVA'] = ((dict_line['flexDW'] * dict_line['MVA_ul']) / 100)
        flex_line['flexDW MW'] = ((dict_line['flexDW'] * dict_line['MVA_ul']) / 100) * self.pf_net
        flex_line['flexDW MVar'] = ((dict_line['flexDW'] * dict_line['MVA_ul']) / 100) * math.sin(math.acos(self.pf_net))

        # DSO needs of flexibility - TRAFOS
        flex_trafo = dict()
        flex_trafo['time'] = _iter * np.ones((len(dict_trafo['idx_ol']), 1))
        flex_trafo['line_ol'] = dict_trafo['idx_ol']
        flex_trafo['overload %'] = dict_trafo['overload']
        flex_trafo['flexUP %'] = dict_trafo['flexUP']
        flex_trafo['flexUP MVA'] = ((dict_trafo['flexUP'] * dict_trafo['MVA_ol']) / 100)
        flex_trafo['flexUP MW'] = ((dict_trafo['flexUP'] * dict_trafo['MVA_ol']) / 100) * self.pf_net
        flex_trafo['flexUP MVar'] = ((dict_trafo['flexUP'] * dict_trafo['MVA_ol']) / 100) * math.sin(math.acos(self.pf_net))
        flex_trafo['line_ul'] = dict_trafo['idx_ul']
        flex_trafo['underload %'] = dict_trafo['undeload']
        flex_trafo['flexDW %'] = dict_trafo['flexDW']
        flex_trafo['flexDW MVA'] = ((dict_trafo['flexDW'] * dict_trafo['MVA_ul']) / 100)
        flex_trafo['flexDW MW'] = ((dict_trafo['flexDW'] * dict_trafo['MVA_ul']) / 100) * self.pf_net
        flex_trafo['flexDW MVar'] = ((dict_trafo['flexDW'] * dict_trafo['MVA_ul']) / 100) * math.sin(math.acos(self.pf_net))

        # DSO needs of flexibility - NODES
        # Da rivedere meglio per il calcolo del MVA
        flex_node = dict()
        flex_node['time'] = _iter * np.ones((len(dict_node['idx_ol']), 1))
        flex_node['line_ol'] = dict_node['idx_ol']
        flex_node['overload %'] = dict_node['overload']
        flex_node['flexUP %'] = dict_node['flexUP']
        flex_node['flexUP MVA'] = ((dict_node['flexUP'] * dict_node['MVA_ol']) / 100)
        flex_node['flexUP MW'] = ((dict_node['flexUP'] * dict_node['MVA_ol']) / 100) * self.pf_net
        flex_node['flexUP MVar'] = ((dict_node['flexUP'] * dict_node['MVA_ol']) / 100) * math.sin(math.acos(self.pf_net))
        flex_node['line_ul'] = dict_node['idx_ul']
        flex_node['underload %'] = dict_node['undeload']
        flex_node['flexDW %'] = dict_node['flexDW']
        flex_node['flexDW MVA'] = ((dict_node['flexDW'] * dict_node['MVA_ul']) / 100)
        flex_node['flexDW MW'] = ((dict_node['flexDW'] * dict_node['MVA_ul']) / 100) * self.pf_net
        flex_node['flexDW MVar'] = ((dict_node['flexDW'] * dict_node['MVA_ul']) / 100) * math.sin(math.acos(self.pf_net))

        # Merge Flexibility request from DSO
        nCONG = len(flex_line['time']) + len(flex_trafo['time']) + len(flex_node['time'])

        DSO_Req = {'flexUP_line MW': flex_line['flexUP MW'],
                    'flexDW_line MW': flex_line['flexDW MW'],
                    'flexUP_trafo MW': flex_trafo['flexUP MW'],
                    'flexDW_trafo MW': flex_trafo['flexDW MW'],
                    'flexUP_node MW': flex_node['flexUP MW'],
                    'flexDW_node MW': flex_node['flexDW MW']}

        return nCONG, DSO_Req

    def _getsens(self):
        """Sensitivity Factors calculation for each congestion point"""
        H_data = list()

        for i in self.list_p.values():
            # Sensitivity factor from PTDF matrix
            H_data.append([self.ptdf.loc[j.node, self.net._pd2ppc_lookups['bus'][int(i.node)]] for j in self.list_p.values()])
        # Resize element
        FSPs_H = np.resize(H_data, (self.nFSP, self.nFSP))

        # For each flexibility service provider (FSP),
        # calculate each congestion point sensitivity factor and put it in the matrix.
        # *** "H_data" --> H_data will be shown with 4 elements, but not in a matrix way
        # *** "FSPs_H" --> FSPs_H will be shown as a array of the same value but rounded
        Factors = pd.DataFrame(FSPs_H,
                               index=['FSP' + str(i + 1) for i in range(self.nFSP)],
                               columns=[self.list_p[_k].node for _k in self.list_p.keys()]).round(3)

        self.sens_mat = FSPs_H
        self.sens_df = Factors

    def setOptModel(self, nCONG, DSO_R, _check):
        """OPTIMIZATION MODEL SETTINGS"""
        self._getsens()

        # Create a new model
        lfm = gp.Model("CM_Market")

        # Upward flexibility from "FSPs LOAD" offer per each period T
        vfU_l = lfm.addMVar(shape=(self.nFSP, 1), lb=0, ub=GRB.INFINITY, vtype=GRB.CONTINUOUS, name="vfU_l")
        # Upward flexibility from "FSPs GEN" offer per each period T
        vfU_g = lfm.addMVar(shape=(self.nFSP, 1), lb=0, ub=GRB.INFINITY, vtype=GRB.CONTINUOUS, name="vfU_g")

        # Downward flexibility from "FSPs LOAD" offer per each period T
        vfD_l = lfm.addMVar(shape=(self.nFSP, 1), lb=0, ub=GRB.INFINITY, vtype=GRB.CONTINUOUS, name="vfD_l")
        # Downward flexibility from "FSPs GEN" offer per each period T
        vfD_g = lfm.addMVar(shape=(self.nFSP, 1), lb=0, ub=GRB.INFINITY, vtype=GRB.CONTINUOUS, name="vfD_g")

        # Flexibility not supplied UP
        vs_U = lfm.addMVar(shape=(nCONG, 1), lb=0, ub=GRB.INFINITY, vtype=GRB.CONTINUOUS, name="vsU")
        # Flexibility not supplied DOWN
        vs_D = lfm.addMVar(shape=(nCONG, 1), lb=0, ub=GRB.INFINITY, vtype=GRB.CONTINUOUS, name="vsD")

        # Max upward flexibility - LOADs
        lfm.addConstr(vfU_l[:, 0] <= self.fspUP_l[:, 0], name="maxfUp_l")
        # Max upward flexibility - GENs
        lfm.addConstr(vfU_g[:, 0] <= self.fspUP_g[:, 0], name="maxfUp_g")

        # Min upward flexibility - LOADs
        lfm.addConstr(vfU_l[:, 0] >= 0, name="minfUp_l")
        # Min upward flexibility - GENs
        lfm.addConstr(vfU_g[:, 0] >= 0, name="minfUp_g")

        # Max downward flexibility - LOADs
        lfm.addConstr(vfD_l[:, 0] <= self.fspDW_l[:, 0], name="maxfDw_l")
        # Max downward flexibility - GENs
        lfm.addConstr(vfD_g[:, 0] <= self.fspDW_g[:, 0], name="maxfDw_g")

        # Min downward flexibility - LOADs
        lfm.addConstr(vfD_l[:, 0] >= 0, name="minfDw_l")
        # Min downward flexibility - GENs
        lfm.addConstr(vfD_g[:, 0] >= 0, name="minfDw_g")

        try:
            # Constraints UP
            for r in range(nCONG):
                lfm.addConstr(
                    DSO_R['flexUP_line MW'][r][0] * 1e3
                    + sum(self.sens_mat[f, r] * vfU_l[f, 0] for f in range(self.nFSP))
                    - sum(self.sens_mat[f, r] * vfU_g[f, 0] for f in range(self.nFSP))
                    - vs_U[r, 0] <= 0,
                    name="Cnst_fUP_" + str(r))
        except IndexError:
            pass

        # Constraints DOWN
        try:
            for r in range(nCONG):
                lfm.addConstr(
                    abs(DSO_R['flexDW_line MW'][r][0]) * 1e3
                    - sum(self.sens_mat[f, r] * vfD_l[f, 0] for f in range(self.nFSP))
                    + sum(self.sens_mat[f, r] * vfD_g[f, 0] for f in range(self.nFSP))
                    - vs_D[r, 0] <= 0,
                    name="Cnst_fDW_" + str(r))
        except IndexError:
            pass

        # Objective Functions
        # Costo variabili slack
        fst_term = sum((self.fspUPc_l[f, 0]) * vfU_l[f, 0] for f in range(self.nFSP))
        snd_term = sum((self.fspUPc_g[f, 0]) * vfU_g[f, 0] for f in range(self.nFSP))
        trd_term = sum((self.fspDWc_l[f, 0]) * vfD_l[f, 0] for f in range(self.nFSP))
        fourth_term = sum((self.fspDWc_g[f, 0]) * vfD_g[f, 0] for f in range(self.nFSP))
        fifth_term = sum((self.cost_s * vs_U[r, 0]) for r in range(nCONG))
        sixth_term = sum((self.cost_s * vs_D[r, 0]) for r in range(nCONG))
        obj_fcn = fst_term + snd_term + trd_term + fourth_term + fifth_term + sixth_term
        lfm.setObjective(obj_fcn, GRB.MINIMIZE)

        # Set the value of a parameter to a new value. ex  m.setParam('MIPGap', 0) or m.Params.MIPGap=0.
        # MIPGap Gurobi will stop when it finds a solution within a percentage of optimal
        lfm.setParam(GRB.Param.MIPGap, 0.1)

        # Write Model on file to check correctness
        if _check:
            lfm.write('LFM_Test_case.lp')

        # Optimise
        lfm.optimize()

        vars = {'vfU_l': vfU_l, 'vfU_g': vfU_g, 'vfD_l': vfD_l, 'vfD_g': vfD_g, 'vs_U': vs_U, 'vs_D': vs_D}

        return lfm, vars

    def extractOptValue(self, vars, nCONG):
        """Estrai i valori ottimali dalla soluzione del problema lineare"""

        vFU_l = pd.DataFrame(vars['vfU_l'].X, index=['Node' + str(i+1) for i in range(self.nFSP)], columns=['FSP Flex Upward Loads [kWh]'])
        vFU_g = pd.DataFrame(vars['vfU_g'].X, index=['Node' + str(i+1) for i in range(self.nFSP)], columns=['FSP Flex Upward Gens [kWh]'])
        vFD_l = pd.DataFrame(vars['vfD_l'].X, index=['Node' + str(i+1) for i in range(self.nFSP)], columns=['FSP Flex Downward Loads [kWh]'])
        vFD_g = pd.DataFrame(vars['vfD_g'].X, index=['Node' + str(i+1) for i in range(self.nFSP)], columns=['FSP Flex Downward Gens [kWh]'])
        vs_U = pd.DataFrame(vars['vs_U'].X, index=['Flex not supplied ' + str(i+1) for i in range(nCONG)], columns=['Flex not supplied UP'])
        vs_D = pd.DataFrame(vars['vs_D'].X, index=['Flex not supplied ' + str(i+1) for i in range(nCONG)], columns=['Flex not supplied DW'])

        v_flex = pd.concat([vFU_l, vFU_g, vFD_l, vFD_g], axis=1)
        vs = pd.concat([vs_U, vs_D], axis=1)

        # Total quantity of upward flexibility - LOADs
        totfU_l = vars['vfU_l'].X.sum()
        # Total quantity of upward flexibility - GENs
        totfU_g = vars['vfU_g'].X.sum()

        # Total upward cost ( quantity of upward * the price for each unit ) - LOADs
        totfUc_l = vars['vfU_l'].X * self.fspUPc_l
        # Total upward cost ( quantity of upward * the price for each unit ) - GENs
        totfUc_g = vars['vfU_g'].X * self.fspUPc_g

        # Total quantity of downward flexibility - LOADs
        totfD_l = vars['vfD_l'].X.sum()
        # Total quantity of downward flexibility - GENs
        totfD_g = vars['vfD_g'].X.sum()

        # Total downward cost ( quantity of downward * the price for each unit ) - LOADs
        totfDc_l = vars['vfD_l'].X * self.fspDWc_l
        # Total downward cost ( quantity of downward * the price for each unit ) - GENs
        totfDc_g = vars['vfD_g'].X * self.fspDWc_g

        # Total UNSERVED quantity UP
        tot_fSUP = vars['vs_U'].X.sum()
        # Total UNSERVED quantity DOWN
        tot_fSDW = vars['vs_D'].X.sum()
        # Total UNSERVED cost ( quantity of UNSERVED * the price for each unit ) - UP
        tot_fScUP = vars['vs_U'].X * self.cost_s
        # Total UNSERVED cost ( quantity of UNSERVED * the price for each unit ) - DOWN
        tot_fScDW = vars['vs_D'].X * self.cost_s


        # Summary
        # The quantity
        Summary_MW = [totfU_l, totfU_g, totfD_l, totfD_g, tot_fSUP, tot_fSDW]
        # The price
        Summary_Cost = [totfUc_l.sum(), totfUc_g.sum(), totfDc_l.sum(), totfDc_g.sum(), tot_fScUP.sum(), tot_fScDW.sum()]
        # All together
        Summary = [Summary_MW, Summary_Cost]
        Summary_t = pd.DataFrame(Summary,
                         index=['tot Flex Provided [KW]', 'tot Costs [Euro]'],
                         columns=['flex UP LOADs', 'flex UP GENs', 'flex DOWN LOADs', 'flex DOWN GENs',
                                  'flex Slack UP', 'flex Slack DW'])

        return v_flex, vs, Summary_t

    def addflexibility(self, load_pmw_b, gen_pmw_b, variables):
        """Add Upward and Downward Flexibility to Loads.
         The service is intended in terms of change of generation. Therefore, for loads is the opposite.
            - v_fU: upward services.
                    Hence for loads is a cut of consumption.
            - v_fD: downward services.
                    Hence for loads is an increase of consumption."""

        idx_load = np.asarray(self.net_init.load.bus) - len(self.slack)
        idx_gen = np.asarray(self.net_init.gen.bus) - len(self.slack)

        # L'energia non fornita come flessibilità per risolvere la contingenza sarà divisa tra tutti i carichi.
        # Agiremo solo sui carichi in quanto questi saranno sempre presenti, al contrario dei generatori che saranno
        # e non saranno presenti in basa alla curva di produzione.
        slack_up = sum(variables['vs_U'].X)[0] / len(idx_load)
        slack_dw = sum(variables['vs_D'].X)[0] / len(idx_load)

        new_load_profile = (np.asarray(load_pmw_b).reshape((-1, 1)) - variables['vfU_l'].X[idx_load] + variables['vfD_l'].X[idx_load] - slack_up + slack_dw)
        new_gen_profile = (np.asarray(gen_pmw_b).reshape((-1, 1)) + variables['vfU_g'].X[idx_gen] - variables['vfD_g'].X[idx_gen])

        return new_load_profile, new_gen_profile

    def getnewbusdata(self, _busD, load_prof, gen_prof, res_net, t):
        _busD_aft = cp.deepcopy(_busD)
        # Estraggo i valori delle Batterie e dei veicoli elettrici
        res_storage = res_net['p_Store'][t]

        idx_bus = np.asarray(self.net_init.bus.index.drop(self.slack)) - len(self.slack)
        idx_load = np.asarray(self.net_init.load.bus) - len(self.slack)
        idx_gen = np.asarray(self.net_init.gen.bus) - len(self.slack)
        idx_store = np.asarray(self.net_init.storage.bus) - len(self.slack)

        # Create Series of Gen and replace with current production value
        z_gen = np.zeros((len(idx_bus), 1))
        z_gen[idx_gen] = gen_prof * 1e-3

        # Create Series of Load and replace with current production value
        z_load = np.zeros((len(idx_bus), 1))
        z_load[idx_load] = load_prof * 1e-3

        # Create Series of Storage and replace with current mw value
        z_store = np.zeros((len(idx_bus), 1))
        z_store[idx_store] = np.array(res_storage, ndmin=2).transpose() * 1e-3

        # Sostituisci i valori netti ai bus
        _busD_aft.net_p_mw = z_load + z_store - z_gen

        return _busD_aft

    def plotdata(self, data, xlab, ylab, plt_title):
        """Function for plotting data"""
        plt.plot(data, label="line_loading")
        plt.xlabel(xlab)
        plt.ylabel(ylab)
        plt.title(plt_title)
        plt.grid()
        plt.show()

    def makeoffer(self, res_net, _iter):
        """Crea le offerte di energia in aumento e in diminuzione degli FSP.
        Gli FSP partecipanti saranno quelli il cui netto al punto di connessione è maggiore o minore di zero.
        In questo modo facciamo una valutazione sulla massimizzazione dell'autoconsumo degli utenti."""
        res_pLoad, res_pGen, res_peer = res_net['p_Load'][_iter], res_net['p_Gen'][_iter], res_net['p_peer'][_iter][1:]
        ppeer = np.array(res_peer, ndmin=2).transpose()
        pLoad = np.zeros((len(ppeer), 1))
        pGen = np.zeros((len(ppeer), 1))
        pmax_L = np.zeros((len(ppeer), 1))
        pmax_G = np.zeros((len(ppeer), 1))
        name_g = pd.Series(np.zeros(len(ppeer)))

        idx_zeros = ppeer.nonzero()[0]
        idx_load = np.asarray(self.net_init.load.bus) - len(self.slack)
        idx_gen = np.asarray(self.net_init.gen.bus) - len(self.slack)

        pLoad[idx_load] = np.array(res_pLoad, ndmin=2).transpose()
        pGen[idx_gen] = np.array(res_pGen, ndmin=2).transpose()

        pmax_L[idx_load] = np.array(self.net_init.load.p_mw, ndmin=2).transpose() * 1e3
        pmax_G[idx_gen] = np.array(self.net_init.gen.p_mw, ndmin=2).transpose() * 1e3

        name_g[idx_gen] = list(self.net_init.gen.name)

        # Upward Power: dal punto di vista dei generatori.
        #   * Gen: incremento generazione (se possibile)
        up_pwG = np.zeros((len(ppeer), 1))
        up_costG = np.zeros((len(ppeer), 1))
        #   * Load: taglio del carico (se possibile)
        up_pwL = np.zeros((len(ppeer), 1))
        up_costL = np.zeros((len(ppeer), 1))

        # Downward Power: dal punto di vista dei generatori.
        #   * Gen: taglio della generazione (se possibile)
        down_pwG = np.zeros((len(ppeer), 1))
        down_costG = np.zeros((len(ppeer), 1))
        #   * Load: incremento del carico (se possibile)
        down_pwL = np.zeros((len(ppeer), 1))
        down_costL = np.zeros((len(ppeer), 1))

        # Define upward power of User [kW]
        gen_idx = np.logical_and(np.logical_and(name_g != 'PV', name_g != 0), [i in idx_zeros for i in idx_load])
        up_pwG[gen_idx] = pmax_G[gen_idx] - pGen[gen_idx]

        load_idx = [i in idx_zeros for i in idx_load]
        up_pwL[load_idx] = 0.5 * pLoad[load_idx]

        # Define downward power of User [kW]
        down_pwG[gen_idx] = pGen[gen_idx]
        down_pwL[load_idx] = pmax_L[load_idx] - pLoad[load_idx]

        # Define upward cost of User [euro/kWh]
        up_costL[load_idx] = np.random.normal(self.max_off, self.min_off, (len([load_idx]), 1))
        up_costG[gen_idx] = np.random.normal(self.max_off, self.min_off, (len([gen_idx]), 1))

        # Define downward cost of User [euro/kWh]
        down_costL[load_idx] = np.random.normal(self.max_off, self.min_off, (len([load_idx]), 1))
        down_costG[gen_idx] = np.random.normal(self.max_off, self.min_off, (len([gen_idx]), 1))

        # Save bids
        self.fspUP_g = np.tile(up_pwG, (1, _iter))
        self.fspUP_l = np.tile(up_pwL, (1, _iter))
        self.fspDW_g = np.tile(down_pwG, (1, _iter))
        self.fspDW_l = np.tile(down_pwL, (1, _iter))
        self.fspUPc_g = np.tile(up_costG, (1, _iter))
        self.fspUPc_l = np.tile(up_costL, (1, _iter))
        self.fspDWc_g = np.tile(down_costG, (1, _iter))
        self.fspDWc_l = np.tile(down_costL, (1, _iter))

        return np.where(load_idx)


if __name__ == "__main__":
    np.random.seed(0)

    # Load network from files
    net = rnet.Net(r'Networks\16nodes_wcong.dat')

    # Create and extract PandaPower network from files
    pp_network = ppnet.PPnet(net).emptyNet

    # Create class for running personalize power flow
    c_pf = rpf.pf(pp_network, net)

    pf_net = 0.96
    cm = CMmarket(pf_net, pp_network, Participant())

    # Esegui power flow T volte
    for t in range(c_pf.time):
        print(' ')
        print('--------------------------------------------', t, '--------------------------------------------')
        # Set SoC of previous state
        bus_data = c_pf.evalsoc(t)

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
            cm.makeoffer(res_net, t)

            # Optimise
            model_opt, vars = cm.setOptModel(nCONG, req_flex, True)
            v_flex, v_slack, summary = cm.extractOptValue(vars, nCONG)
            print(' ')
            print('slack: ',  v_slack)

            # Include flexibility
            new_load_profile, new_gen_profile = cm.addflexibility(res_net['p_Load'][t], res_net['p_Gen'][t], vars)

            # Get new bus data
            bus_data_aft = cm.getnewbusdata(bus_data, new_load_profile, new_gen_profile, res_net, t)

            # Run PF
            check_cons = c_pf.runPF(bus_data_aft)
            c_pf.change_elementDf(t, pd.Series(res_net['p_Store'][t]), new_gen_profile, new_load_profile)

            # Save data
            c_pf.savevar(t)

    # Salva i dati
    c_pf.savedf()

    # Estrai i dati
    df_net = c_pf.df_net
