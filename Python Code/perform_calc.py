from Networks import readNet as rnet
from Networks import setPPnet as ppnet
from Networks import runpf as rpf
import central_market_v2 as da
import cda_alg as cda
import pcda_alg as pcda
import flex_market as flex
import eval_file as ef
import numpy as np
import copy as cp
import pandas as pd


if __name__ == "__main__":
    # Set fixed SEED
    np.random.seed(0)

    _case = 'PCDA'
    if _case == 'DA':
        # File per salvataggio - Double Auction market (Centralised)
        filename = 'Results\centralmarket_pv.xlsx'
    elif _case == 'CDA':
        # File per salvataggio - Pseudo Continuous Double Auction market (Distributed)
        filename = 'Results\cda_market_pv.xlsx'
    elif _case == 'PCDA':
        # File per salvataggio - Pseudo Continuous Double Auction market (Distributed)
        filename = 'Results\pcda_market_pv.xlsx'

    # Load network from files
    net = rnet.Net('Networks\LV_16nodi.dat')

    # Create and extract PandaPower network from files
    pp_network = ppnet.PPnet(net).emptyNet

    # Create class for running personalize power flow
    c_pf = rpf.pf(pp_network, net)

    # Power Factor of the net
    pf_net = 0.96
    # Congestion management market class
    cm = flex.CMmarket(pf_net, pp_network, cda.Participant())

    # Prezzo di vendita alla rete
    # 25 EURO/MWh (0.025 EURO/kWh)
    sellGrid = 0.025
    # Prezzo di acquisto dalla rete
    # 400 EURO/MWh (0.4 EURO/kWh)
    buyGrid = 0.4

    m_da = da.DAmarket(c_pf, pp_network, buyGrid, sellGrid, da.Contract())
    m_cda = cda.CDAmarket(sellGrid, buyGrid, pp_network, cda.Contract(), cda.Participant(), cda.bck())
    m_pcda = pcda.PCDAmarket(sellGrid, buyGrid, pp_network, pcda.Contract(), pcda.Participant(), pcda.bck())

    # Inserisci i giusti partecipanti
    m_cda.Participant = {_k: cp.deepcopy(m_da.list_p[_k]) for _k in list(m_da.list_p.keys())[1:len(m_da.list_p.keys())]}
    m_cda.master = cp.deepcopy(m_da.list_p[list(m_da.list_p.keys())[0]])
    m_pcda.Participant = {_k: cp.deepcopy(m_da.list_p[_k]) for _k in list(m_da.list_p.keys())[1:len(m_da.list_p.keys())]}
    m_pcda.master = cp.deepcopy(m_da.list_p[list(m_da.list_p.keys())[0]])

    cm.list_p = {_k: cp.deepcopy(m_da.list_p[_k]) for _k in list(m_da.list_p.keys())[1:len(m_da.list_p.keys())]}

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
            m_da.marketoffers(bus_data, t)

            if _case == 'DA':
                # ---------------Matching DA----------------
                m_da.matching(t, bus_data)

                # Save data
                c_pf.savevar(t)

            elif _case == 'CDA':
                m_cda.marketoffers(t, bus_data)

                # Modifica il libro del mercato
                m_cda.pre_book[t] = m_da.book

                # --------------Matching CDA----------------
                n_user_left = len(m_cda.rand_list)
                while n_user_left > 0:
                    # -------------Place Offer-------------
                    n_user_left = m_cda.randomplace(t)

                    # --------------Matching---------------
                    m_cda.cda(t)

                    # Run PF
                    check_cons = c_pf.runPF(bus_data)

                    # Get result of network
                    c_pf.savevar(t)
                    res_net = c_pf.res_net

                    if not check_cons:
                        # Inseriamo una copia della rete pandapower (con i risultati del power flow) dentro la classe CMmarket
                        cm.net = cp.deepcopy(c_pf.network_pp)

                        # Elaborate parameters for optimisation
                        nCONG, DSO_Req, _, _ = cm.evalnet(t, res_net['line'][t], res_net['trafo'][t])

                        # Make Offers (only loads can offer flexibility - "for now")
                        cm.makeoffer(res_net['p_Load'][t], t)

                        # Aggiungiamo il tempo di caricare l'offerta di ogni utente
                        # nella lista dei tempi blockchain della classe PCDAmarket
                        m_cda.addTime(t, _case=True)

                        # Optimise
                        model_opt, vars = cm.setOptModel(nCONG, DSO_Req, False)
                        v_flex, v_slack, Summary = cm.extractOptValue(vars, nCONG)

                        # Aggiungiamo il tempo di caricare la soluzione del SO nella lista dei tempi della classe PCDAmarket
                        m_cda.addTime(t, _case=False)

                        # Include flexibility
                        new_load_profile = cm.addflexibility(res_net['p_Load'][t], vars)

                        # Get new bus data
                        bus_data = cm.getnewbusdata(bus_data, new_load_profile, res_net['p_Gen'][t],
                                                    res_net['p_Store'][t])

                        # Run PF
                        check_cons = c_pf.runPF(bus_data)
                        c_pf.change_elementDf(t, pd.Series(res_net['p_Store'][t]), pd.Series(res_net['p_Gen'][t]),
                                              new_load_profile)

                        # Save data
                        c_pf.savevar(t)

                        # Distribute costs towards peers included in the P2P market
                        m_cda.includeflexcost(t, v_flex, v_slack, Summary)

            elif _case == 'PCDA':
                m_pcda.marketoffers(t, bus_data)

                # Modifica il libro del mercato
                m_pcda.book[t] = m_da.book

                # --------------Matching PCDA---------------
                m_pcda.cda(t)

                # Run PF
                check_cons = c_pf.runPF(bus_data)

                # Get result of network
                c_pf.savevar(t)
                res_net = c_pf.res_net

                if not check_cons:
                    # Inseriamo una copia della rete pandapower (con i risultati del power flow) dentro la classe CMmarket
                    cm.net = cp.deepcopy(c_pf.network_pp)

                    # Elaborate parameters for optimisation
                    nCONG, DSO_Req, _, _ = cm.evalnet(t, res_net['line'][t], res_net['trafo'][t])

                    # Make Offers (only loads can offer flexibility - "for now")
                    cm.makeoffer(res_net['p_Load'][t], t)

                    # Aggiungiamo il tempo di caricare l'offerta di ogni utente
                    # nella lista dei tempi blockchain della classe PCDAmarket
                    m_pcda.addTime(t, _case=True)

                    # Optimise
                    model_opt, vars = cm.setOptModel(nCONG, DSO_Req, False)
                    v_flex, v_slack, Summary = cm.extractOptValue(vars, nCONG)

                    # Aggiungiamo il tempo di caricare la soluzione del SO nella lista dei tempi della classe PCDAmarket
                    m_pcda.addTime(t, _case=False)

                    # Include flexibility
                    new_load_profile = cm.addflexibility(res_net['p_Load'][t], vars)

                    # Get new bus data
                    bus_data = cm.getnewbusdata(bus_data, new_load_profile, res_net['p_Gen'][t], res_net['p_Store'][t])

                    # Run PF
                    check_cons = c_pf.runPF(bus_data)
                    c_pf.change_elementDf(t, pd.Series(res_net['p_Store'][t]), pd.Series(res_net['p_Gen'][t]),
                                          new_load_profile)

                    # Save data
                    c_pf.savevar(t)

                    # Distribute costs towards peers included in the P2P market
                    m_pcda.includeflexcost(t, v_flex, v_slack, Summary)

        # Save times on Excel
        # if _case == 'DA':
        #     list_ctimes[_i] = m_da.collecttimes()
        # elif _case == 'CDA':
        #     list_ctimes[_i] = m_cda.collecttimes()
        # elif _case == 'PCDA':
        #     list_ctimes[_i] = m_pcda.collecttimes()

    # c_pf.write_excel(filename=filename, sheet_name='Time Eval', data=list_ctimes)
    # exit()

    # Extract list of contracts
    if _case == 'DA':
        list_cntr = m_da.set_list()
    elif _case == 'CDA':
        list_cntr = m_cda.set_list()
    elif _case == 'PCDA':
        list_cntr = m_pcda.set_list()

    # Save list of contracts on Excel
    c_pf.write_excel(filename=filename, sheet_name='Market times', data=list_cntr)

    # Save data on DataFrame
    c_pf.savedf()

    # Extract Data
    df_net = c_pf.df_net

    # Save networks results on Excel
    c_pf.write_excel(filename=filename, sheet_name='ppeer_kw', data=df_net['ppeer_df'])
    c_pf.write_excel(filename=filename, sheet_name='qpeer_kvar', data=df_net['qpeer_df'])
    c_pf.write_excel(filename=filename, sheet_name='vmpeer', data=df_net['vmpeer_df'])
    c_pf.write_excel(filename=filename, sheet_name='pLoad', data=df_net['pLoad_df'])
    c_pf.write_excel(filename=filename, sheet_name='pGen', data=df_net['pGen_df'])
    c_pf.write_excel(filename=filename, sheet_name='pStore', data=df_net['pStore_df'])
    c_pf.write_excel(filename=filename, sheet_name='pVeicolo', data=df_net['pVeicolo_df'])
    c_pf.write_excel(filename=filename, sheet_name='SoC_storage', data=df_net['SoC_df'])
    c_pf.write_excel(filename=filename, sheet_name='Line Loading', data=df_net['line_df'])
    c_pf.write_excel(filename=filename, sheet_name='Trafo Loading', data=df_net['trafo_df'])

    # Save Users and addresses on Excel
    if _case == 'DA':
        c_pf.write_excel(filename=filename,
                         sheet_name='User addresses',
                         data={'address': m_da.k_addrs, 'node': [m_da.list_p[k].node for k in m_da.list_p.keys()]})

        eval_class = ef.eval(m_da.contracts, buyGrid, sellGrid, m_da.list_p, m_da.list_p[list(m_da.list_p.keys())[0]].add, c_pf)
        eval_class.evalSW(False)
        eval_class.evalCQR(False)
        eval_class.writexlsx(filename=filename, sheet_name='Comparison SW', data=eval_class.SW)
        eval_class.writexlsx(filename=filename, sheet_name='Comparison DW', data=eval_class.DW)
        eval_class.writexlsx(filename=filename, sheet_name='Comparison CQR', data=eval_class.CQR)
        eval_class.writexlsx(filename=filename, sheet_name='Comparison tot bid', data=eval_class.tot_bid)

    elif _case == 'CDA':
        c_pf.write_excel(filename=filename,
                         sheet_name='User addresses',
                         data={'address': m_cda.Participant.keys(),
                               'node': [m_cda.Participant[k].node for k in m_cda.Participant.keys()]})

        eval_class = ef.eval(m_cda.Contract, buyGrid, sellGrid, m_cda.Participant, m_cda.master.add, c_pf)
        eval_class.evalSW(True)
        eval_class.evalCQR(True)
        eval_class.writexlsx(filename=filename, sheet_name='Comparison SW', data=eval_class.SW)
        eval_class.writexlsx(filename=filename, sheet_name='Comparison DW', data=eval_class.DW)
        eval_class.writexlsx(filename=filename, sheet_name='Comparison CQR', data=eval_class.CQR)
        eval_class.writexlsx(filename=filename, sheet_name='Comparison tot bid', data=eval_class.tot_bid)

    elif _case == 'PCDA':
        c_pf.write_excel(filename=filename,
                         sheet_name='User addresses',
                         data={'address': m_pcda.Participant.keys(),
                               'node': [m_pcda.Participant[k].node for k in m_pcda.Participant.keys()]})

        eval_class = ef.eval(m_pcda.Contract, buyGrid, sellGrid, m_pcda.Participant, m_pcda.master.add, c_pf)
        eval_class.evalSW(True)
        eval_class.evalCQR(True)
        eval_class.writexlsx(filename=filename, sheet_name='Comparison SW', data=eval_class.SW)
        eval_class.writexlsx(filename=filename, sheet_name='Comparison DW', data=eval_class.DW)
        eval_class.writexlsx(filename=filename, sheet_name='Comparison CQR', data=eval_class.CQR)
        eval_class.writexlsx(filename=filename, sheet_name='Comparison tot bid', data=eval_class.tot_bid)
