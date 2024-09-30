from Networks import readNet as rnet
import pandapower as pp
import math
from pandapower.plotting.plotly import pf_res_plotly
import numpy as np


class PPnet:
    def __init__(self, fileDat):
        self.emptyNet = pp.create_empty_network()
        self.Vn = fileDat.DatiReteDistribuzione['Tensione Nominale [kV]']
        self.slack = fileDat.DatiReteDistribuzione['Nodi CP']
        self.n_cp = len(self.slack['N'])
        self.nbus = fileDat.DatiReteDistribuzione['N cabine Secondarie']['Esistenti']
        self.bus = fileDat.DatiReteDistribuzione['Nodi MT']
        self.idx_bus = list()
        self.busGeodata_X = fileDat.DatiReteDistribuzione['Nodi MT']['Coord X']
        self.busGeodata_Y = fileDat.DatiReteDistribuzione['Nodi MT']['Coord Y']
        self.nbranch = fileDat.DatiReteDistribuzione['N Rami Esistenti']
        self.branch = fileDat.DatiReteDistribuzione['Rami']
        self.branchData_cb = fileDat.DatiTecniciEconomiciAffidabilisticiLineeCavo
        self.branchData_oh = fileDat.DatiTecniciEconomiciAffidabilisticiLineeAeree
        self.Trafo = fileDat.DatiTrasformatori
        self.setBus()
        self.setExtgrid()
        self.setLoad()
        self.setTrafo()
        self.setLine()
        self.setGen()
        self.setStorage()
        self.setEV()

    def setBus(self):
        self.idx_bus = [pp.create_bus(self.emptyNet, vn_kv=self.Trafo['Dati per il calcolo dei costi del trasformatore']['Vat_base [kV]'], geodata=(self.slack['Coord X'][idx], self.slack['Coord Y'][idx]), name=('ExtGrid ' + str(idx))) for idx in range(int(self.n_cp))]

        for idx in range(int(self.nbus)):
            self.idx_bus.append(pp.create_bus(self.emptyNet, vn_kv=self.Vn, geodata=(self.busGeodata_X[idx], self.busGeodata_Y[idx]), name='Bus ' + str(idx + self.n_cp)))

    def setExtgrid(self):
        id_extGrid = [pp.create_ext_grid(self.emptyNet, bus=(self.slack['N'][idx] - 1), slack=True) for idx in range(self.n_cp)]
        [pp.create_pwl_cost(self.emptyNet, id_extGrid[idx], 'ext_grid', [[0, 1000, 0]]) for idx in range(len(id_extGrid))]

    def setLoad(self):
        Pc = [self.bus['Pc [kW]'][idx] * 1e-3 for idx in range(len(self.bus['Pc [kW]']))]

        Sc = list()
        Qc = list()
        for idx in range(len(self.bus['Pc [kW]'])):
            try:
                Sc.append((self.bus['Pc [kW]'][idx] * 1e-3)/self.bus['Cosfic'][idx])
                Qc.append(Sc[idx] * math.sin(math.acos(self.bus['Cosfic'][idx])))
            except ZeroDivisionError:
                Sc.append(0)
                Qc.append(0)

        # Eliminaimo lo slack bus dagli indici dei bus
        index_ExtGrid = [int(self.emptyNet.ext_grid.loc[idx, 'bus']) for idx in range(self.n_cp)]
        index_Bus = []
        for i in self.idx_bus:
            if i not in index_ExtGrid:
                index_Bus.append(i)

        pp.create_loads(self.emptyNet, buses=index_Bus, p_mw=Pc, q_mvar=Qc)

    def setTrafo(self):
        trafoNorm = self.Trafo['Trasformatore Normalizzato']
        trafoNonNorm = self.Trafo['Trasformatore Non Normalizzato']
        brFrom = self.branch['From']
        brTo = self.branch['To']

        for i in range(len(self.slack['N'])):
            n_trafo = self.slack['N Trasf.']
            if n_trafo[i] > self.Trafo['Tipi di Trasformatori']['Normalizzati']:
                typeTrafo = trafoNonNorm
            else:
                typeTrafo = trafoNorm

            hv_bus = self.slack['N'][i] - 1
            lv_bus = brTo[brFrom.index(hv_bus + 1)] - 1
            vn_hv_kv = self.Trafo['Dati per il calcolo dei costi del trasformatore']['Vat_base [kV]']
            pfe_kW = typeTrafo['P_vuoto [kW]'][i]
            pcc_p = ((typeTrafo['P_carico [kW]'][i] * 1e-3)/typeTrafo['Taglia [MVA]'][i]) * 100
            i0_p = ((typeTrafo['P_vuoto [kW]'][i] * 1e-3)/typeTrafo['Taglia [MVA]'][i]) * 100
            vcc = typeTrafo['Vcc [%]'][i]
            vcc_r = pcc_p/100 * (self.Vn ** 2/(typeTrafo['Taglia [MVA]'][i]))
            sn = (typeTrafo['Taglia [MVA]'][i])
            pp.create_transformer_from_parameters(self.emptyNet, sn_mva=sn, hv_bus=hv_bus, lv_bus=lv_bus,
                                                  vn_hv_kv=vn_hv_kv, vn_lv_kv=self.Vn, i0_percent=i0_p,
                                                  pfe_kw=pfe_kW, vk_percent=vcc, vkr_percent=vcc_r)

    def setLine(self):
        brFrom = [self.branch['From'][j] - 1 for j in range(len(self.branch['From']))]
        brTo = [self.branch['To'][j] - 1 for j in range(len(self.branch['To']))]
        idxBr_oh = self.branch['Indice Sezione Aerea']
        idxBr_cb = self.branch['Indice Sezione Cavo']
        brStatus = self.branch['Stato Connessione']
        brLength_oh = self.branch['L Aerea [m]']
        brLength_cb = self.branch['L Cavo [m]']
        n_brNorm_oh = self.branchData_oh['Tipi di Conduttore Aereo']['Normalizzati']
        n_brNorm_cb = self.branchData_cb['Tipi di Conduttore Cavo']['Normalizzati']
        r_km = list()
        x_km = list()
        c_km = list()
        ampacity = list()
        L_br = list()
        status = list()

        for idx in range(len(brFrom)):
            if brStatus[idx] == 'C':
                status.append(True)
            else:
                status.append(False)

            if brLength_cb[idx] == 0:
                L_br.append(brLength_oh[idx] * 1e-3)
                if idxBr_oh[idx] > n_brNorm_oh:
                    r_km.append(self.branchData_oh['Conduttore Aereo Non Normalizzato']['R[Ohm/km]'][int(idxBr_oh[idx]-n_brNorm_oh-1)])
                    x_km.append(self.branchData_oh['Conduttore Aereo Non Normalizzato']['X[Ohm/km]'][int(idxBr_oh[idx]-n_brNorm_oh-1)])
                    c_km.append(self.branchData_oh['Conduttore Aereo Non Normalizzato']['C[microF/km]'][int(idxBr_oh[idx]-n_brNorm_oh-1)] * 1e3)
                    ampacity.append(self.branchData_oh['Conduttore Aereo Non Normalizzato']['Portata [A]'][int(idxBr_oh[idx]-n_brNorm_oh-1)] * 1e-3)
                else:
                    r_km.append(self.branchData_oh['Conduttore Aereo Normalizzato']['R[Ohm/km]'][int(idxBr_oh[idx]-1)])
                    x_km.append(self.branchData_oh['Conduttore Aereo Normalizzato']['X[Ohm/km]'][int(idxBr_oh[idx]-1)])
                    c_km.append(self.branchData_oh['Conduttore Aereo Normalizzato']['C[microF/km]'][int(idxBr_oh[idx]-1)] * 1e3)
                    ampacity.append(self.branchData_oh['Conduttore Aereo Normalizzato']['Portata [A]'][int(idxBr_oh[idx]-1)] * 1e-3)
            else:
                L_br.append(brLength_cb[idx] * 1e-3)
                if idxBr_cb[idx] > n_brNorm_cb:
                    r_km.append(self.branchData_cb['Conduttore Cavo Non Normalizzato']['R[Ohm/km]'][int(idxBr_cb[idx]-n_brNorm_cb-1)])
                    x_km.append(self.branchData_cb['Conduttore Cavo Non Normalizzato']['X[Ohm/km]'][int(idxBr_cb[idx]-n_brNorm_cb-1)])
                    c_km.append(self.branchData_cb['Conduttore Cavo Non Normalizzato']['C[microF/km]'][int(idxBr_cb[idx]-n_brNorm_cb-1)] * 1e3)
                    ampacity.append(self.branchData_cb['Conduttore Cavo Non Normalizzato']['Portata [A]'][int(idxBr_cb[idx]-n_brNorm_cb-1)] * 1e-3)
                else:
                    r_km.append(self.branchData_cb['Conduttore Cavo Normalizzato']['R[Ohm/km]'][int(idxBr_cb[idx]-1)])
                    x_km.append(self.branchData_cb['Conduttore Cavo Normalizzato']['X[Ohm/km]'][int(idxBr_cb[idx]-1)])
                    c_km.append(self.branchData_cb['Conduttore Cavo Normalizzato']['C[microF/km]'][int(idxBr_cb[idx]-1)] * 1e3)
                    ampacity.append(self.branchData_cb['Conduttore Cavo Normalizzato']['Portata [A]'][int(idxBr_cb[idx]-1)] * 1e-3)

        pp.create_lines_from_parameters(self.emptyNet, from_buses=brFrom, to_buses=brTo, length_km=L_br,
                                        r_ohm_per_km=r_km, x_ohm_per_km=x_km, c_nf_per_km=c_km, max_i_ka=ampacity,
                                        in_service=status)

    def setGen(self):
        Ag = [self.bus['Ag [kVA]'][idx] for idx in range(len(self.bus['Ag [kVA]']))]
        cosfig = [self.bus['Cosifg'][idx] for idx in range(len(self.bus['Cosifg']))]
        Pg_b = [Ag[idx] * cosfig[idx] for idx in range(len(Ag))]
        Pg = []
        indexGen = []
        for idx in range(len(Pg_b)):
            if Pg_b[idx] != 0:
                Pg.append(Pg_b[idx] * 1e-3)
                indexGen.append(idx + self.n_cp)

        list_idGen = [pp.create_gen(self.emptyNet, bus=indexGen[idx], p_mw=Pg[idx], min_p_mw=0, max_p_mw=0) for idx in range(len(Pg))]
        [pp.create_pwl_cost(self.emptyNet, list_idGen[idx], 'gen', [[0, 0, 0]]) for idx in range(len(list_idGen))]

    def setStorage(self):
        Ps = [self.bus['Pstorage [kW]'][idx] for idx in range(len(self.bus['Pstorage [kW]']))]
        indexStorage = []
        Ps_fin = []
        min_e = []
        max_e = []
        soc_init = []
        for idx in range(len(Ps)):
            if Ps[idx] != 0:
                Ps_fin.append(Ps[idx] * 1e-3)
                # Come valore max di Capacità mettiamo la Capacità della batteria - success. mettiamo 0.9 come limite
                max_e.append(self.bus['Estorage [kWh]'][idx] * 1e-3)
                min_e.append(self.bus['Emin [kWh]'][idx] * 1e-3)
                soc_init.append(self.bus['Initial SoC [%]'][idx])
                indexStorage.append(idx + self.n_cp)

        [pp.create_storage(self.emptyNet, bus=indexStorage[idx], p_mw=Ps_fin[idx], max_e_mwh=max_e[idx], min_e_mwh=min_e[idx], soc_percent=soc_init[idx], name='Storage#'+str(idx)) for idx in range(len(Ps_fin))]

    def setEV(self):
        cs = [self.bus['Charging Station [kW]'][idx] for idx in range(len(self.bus['Charging Station [kW]']))]
        cs_fin = []
        index_ev = []
        cap = []
        for idx in range(len(cs)):
            if cs[idx] != 0:
                cs_fin.append(cs[idx] * 1e-3)
                index_ev.append(idx + self.n_cp)
                # Definisci capacità della batteria del veicolo
                mu, sigma = 57 * 1e-3, 15 * 1e-3  # MWh
                cap.append(np.random.normal(loc=mu, scale=sigma, size=1)[0])

        [pp.create_storage(self.emptyNet, bus=index_ev[idx], p_mw=cs_fin[idx], max_e_mwh=cap[idx], name='EV#'+str(idx)) for idx in range(len(cs_fin))]


if __name__ == "__main__":
    net = rnet.Net('LV_16nodi.dat')

    ppNet_class = PPnet(net)
    pp_network = ppNet_class.emptyNet
    print(pp_network)

    pp.runpp(pp_network)
    print(1)
    pf_res_plotly(pp_network)
