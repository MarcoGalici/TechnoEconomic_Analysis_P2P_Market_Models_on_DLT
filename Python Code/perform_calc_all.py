from Networks import readNet as rnet
from Networks import setPPnet as ppnet
from Networks import runpf as rpf
import central_market as da
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

    # File per salvataggio - Double Auction market (Centralised)
    filename_DA = 'Results\centralmarket_test251122.xlsx'
    # File per salvataggio - Pseudo Continuous Double Auction market (Distributed)
    filename_CDA = 'Results\cda_market_test251122.xlsx'
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
    cm = flex.CMmarket(pf_net, pp_network, cda.Participant())

    # Prezzo di vendita alla rete
    # 25 EURO/MWh (0.025 EURO/kWh)
    sellGrid = 0.025
    # Prezzo di acquisto dalla rete
    # 400 EURO/MWh (0.4 EURO/kWh)
    buyGrid = 0.4

    # Negotiation time [30 minuti]
    neg_time_da = 30 * 60
    # Negotiation time [30 minuti]
    neg_time_pcda = 30 * 60
    # Negotiation time [3 minuti]
    neg_time_cda = 3 * 60

    m_da = da.DAmarket(c_pf, pp_network, buyGrid, sellGrid, da.Contract(), neg_time_da)
    m_cda = cda.CDAmarket(sellGrid, buyGrid, pp_network, cda.Contract(), cda.Participant(), cda.bck(), neg_time_cda, neg_time_da)
    m_pcda = pcda.PCDAmarket(sellGrid, buyGrid, pp_network, pcda.Contract(), pcda.Participant(), pcda.bck(), neg_time_pcda)

    # Inserisci i giusti partecipanti
    m_cda.Participant = {_k: cp.deepcopy(m_da.list_p[_k]) for _k in list(m_da.list_p.keys())[1:len(m_da.list_p.keys())]}
    m_cda.master = cp.deepcopy(m_da.list_p[list(m_da.list_p.keys())[0]])
    m_pcda.Participant = {_k: cp.deepcopy(m_da.list_p[_k]) for _k in list(m_da.list_p.keys())[1:len(m_da.list_p.keys())]}
    m_pcda.master = cp.deepcopy(m_da.list_p[list(m_da.list_p.keys())[0]])

    cm.list_p = {_k: cp.deepcopy(m_da.list_p[_k]) for _k in list(m_da.list_p.keys())[1:len(m_da.list_p.keys())]}

    # --------------------Mercato------------------
    list_ctimes_da = dict()
    list_ctimes_cda = dict()
    list_ctimes_pcda = dict()
    for _i in range(1):
        print(' ')
        print(_i)
        m_cda.set_struct(c_pf.time)
        for t in range(c_pf.time):
            print(t)

            # ------Set previous SoC and Profiles------
            bus_data = c_pf.evalsoc(t)

            # ------------------------------- CENTRALISED DA -------------------------------
            m_da.marketoffers(bus_data, t)

            # ---------------Matching DA----------------
            m_da.matching(t)

            # Run PF
            check_cons = c_pf.runPF(bus_data)

            # Get result of network
            c_pf.savevar(t)
            res_net_da = c_pf.res_net

            if not check_cons:
                # Inseriamo una copia della rete pandapower (con i risultati del power flow) dentro la classe CMmarket
                cm.net = cp.deepcopy(c_pf.network_pp)

                # Elaborate parameters for optimisation
                nCONG_da, DSO_Req_da = cm.evalnet(t, res_net_da)

                # Make Offers (only loads can offer flexibility - "for now")
                fsp_da = cm.makeoffer(res_net_da, t)

                # Optimise
                model_opt_da, vars_da = cm.setOptModel(nCONG_da, DSO_Req_da, False)
                v_flex_da, v_slack_da, summary_da = cm.extractOptValue(vars_da, nCONG_da)

                # Include flexibility
                new_load_profile_da, new_gen_profile_da = cm.addflexibility(res_net_da['p_Load'][t], res_net_da['p_Gen'][t], vars_da)

                # Get new bus data
                bus_data_aft_da = cm.getnewbusdata(bus_data, new_load_profile_da, new_gen_profile_da, res_net_da, t)

                # Run PF
                check_cons_da = c_pf.runPF(bus_data_aft_da)
                print(check_cons_da)
                c_pf.change_elementDf(t, pd.Series(res_net_da['p_Store'][t]), new_gen_profile_da, new_load_profile_da)

                # Save data
                c_pf.savevar(t)

                # Distribute costs towards peers included in the P2P market
                m_da.includeflexcost(t, v_flex_da, v_slack_da, summary_da, fsp_da)


            # ------------------------------- DISTRIBUTED CDA -------------------------------
            m_cda.marketoffers(t, bus_data)

            # Modifica il libro del mercato
            m_cda.pre_book[t] = m_da.book

            # ----------------Matching CDA----------------
            n_user_left = len(m_cda.rand_list)
            # Consideriamo un tempo di piazz. Offerte di 30 min e un clear ogni 3 min, quindi 10 clear in totale
            _nclear_max = m_cda.n_claring
            _nclear = 0
            while _nclear < _nclear_max:
                # -------------Place Offer-------------
                n_user_left = m_cda.randomplace(t, _nclear)

                # --------------Matching---------------
                m_cda.cda(t, _nclear)

                bus_data_subint = m_cda.modbusdata(t, bus_data)

                # print("CDA - time: ", t, " - n. clears: ", _nclear)
                # _nclear += 1

                # print(" ")

                # Run PF
                check_cons = c_pf.runPF(bus_data_subint)

                # Get result of network
                c_pf.savevar(t)
                res_net_cda = c_pf.res_net

                if not check_cons:
                    # Inseriamo una copia della rete pandapower dentro la classe CMmarket
                    # (con i risultati del power flow)
                    cm.net = cp.deepcopy(c_pf.network_pp)

                    # Elaborate parameters for optimisation
                    nCONG_cda, DSO_Req_cda = cm.evalnet(t, res_net_cda)

                    # Make Offers (only loads can offer flexibility - "for now")
                    fsp_cda = cm.makeoffer(res_net_cda, t)

                    # Aggiungiamo il tempo di caricare l'offerta di ogni utente
                    # nella lista dei tempi blockchain della classe PCDAmarket
                    m_cda.addTime(t, _case=True)

                    # Optimise
                    model_opt_cda, vars_cda = cm.setOptModel(nCONG_cda, DSO_Req_cda, False)
                    v_flex_cda, v_slack_cda, summary_cda = cm.extractOptValue(vars_cda, nCONG_cda)

                    # Aggiungiamo il tempo di caricare la soluzione del SO nella lista dei tempi della classe PCDAmarket
                    m_cda.addTime(t, _case=False)

                    # Include flexibility
                    new_load_profile_cda, new_gen_profile_cda = cm.addflexibility(res_net_cda['p_Load'][t], res_net_cda['p_Gen'][t], vars_cda)

                    # Get new bus data
                    bus_data_aft_cda = cm.getnewbusdata(bus_data, new_load_profile_cda, new_gen_profile_cda, res_net_cda, t)

                    # Run PF
                    check_cons_cda = c_pf.runPF(bus_data_aft_cda)
                    print(check_cons_cda)
                    c_pf.change_elementDf(t, pd.Series(res_net_cda['p_Store'][t]), new_gen_profile_cda, new_load_profile_cda)

                    # Save data
                    c_pf.savevar(t)

                    # Distribute costs towards peers included in the P2P market
                    m_cda.includeflexcost(t, v_flex_cda, v_slack_cda, summary_cda, fsp_cda)

                _nclear += 1


            # ------------------------------- DISTRIBUTED PCDA -------------------------------
            m_pcda.marketoffers(t, bus_data)

            # Modifica il libro del mercato
            m_pcda.book[t] = m_da.book

            # --------------Matching PCDA---------------
            m_pcda.cda(t)

            # Run PF
            check_cons = c_pf.runPF(bus_data)

            # Get result of network
            c_pf.savevar(t)
            res_net_pcda = c_pf.res_net

            if not check_cons:
                # Inseriamo una copia della rete pandapower (con i risultati del power flow) dentro la classe CMmarket
                cm.net = cp.deepcopy(c_pf.network_pp)

                # Elaborate parameters for optimisation
                nCONG_pcda, DSO_Req_pcda = cm.evalnet(t, res_net_pcda)

                # Make Offers (only loads can offer flexibility - "for now")
                fsp_pcda = cm.makeoffer(res_net_pcda, t)

                # Aggiungiamo il tempo di caricare l'offerta di ogni utente
                # nella lista dei tempi blockchain della classe PCDAmarket
                m_pcda.addTime(t, _case=True)

                # Optimise
                model_opt_pcda, vars_pcda = cm.setOptModel(nCONG_pcda, DSO_Req_pcda, False)
                v_flex_pcda, v_slack_pcda, summary_pcda = cm.extractOptValue(vars_pcda, nCONG_pcda)

                # Aggiungiamo il tempo di caricare la soluzione del SO nella lista dei tempi della classe PCDAmarket
                m_pcda.addTime(t, _case=False)

                # Include flexibility
                new_load_profile_pcda, new_gen_profile_pcda = cm.addflexibility(res_net_pcda['p_Load'][t], res_net_pcda['p_Gen'][t], vars_pcda)

                # Get new bus data
                bus_data_aft_pcda = cm.getnewbusdata(bus_data, new_load_profile_pcda, new_gen_profile_pcda, res_net_pcda, t)

                # Run PF
                check_cons_pcda = c_pf.runPF(bus_data_aft_pcda)
                print(check_cons_pcda)
                c_pf.change_elementDf(t, pd.Series(res_net_pcda['p_Store'][t]), new_gen_profile_pcda, new_load_profile_pcda)

                # Save data
                c_pf.savevar(t)

                # Distribute costs towards peers included in the P2P market
                m_pcda.includeflexcost(t, v_flex_pcda, v_slack_pcda, summary_pcda, fsp_pcda)

        # Save times on Excel
    #     list_ctimes_da[_i] = m_da.collecttimes()
    #     list_ctimes_cda[_i] = m_cda.collecttimes()
    #     list_ctimes_pcda[_i] = m_pcda.collecttimes()
    #
    # c_pf.write_excel(filename=filename_DA, sheet_name='Time Eval', data=list_ctimes_da)
    # c_pf.write_excel(filename=filename_CDA, sheet_name='Time Eval', data=list_ctimes_cda)
    # c_pf.write_excel(filename=filename_PCDA, sheet_name='Time Eval', data=list_ctimes_pcda)
    # exit()

    # Extract list of contracts
    list_cntr_DA = m_da.set_list()
    list_cntr_CDA = m_cda.set_list()
    list_cntr_PCDA = m_pcda.set_list()

    # Save list of contracts on Excel
    c_pf.write_excel(filename=filename_DA, sheet_name='Market times', data=list_cntr_DA)
    c_pf.write_excel(filename=filename_CDA, sheet_name='Market times', data=list_cntr_CDA)
    c_pf.write_excel(filename=filename_PCDA, sheet_name='Market times', data=list_cntr_PCDA)

    # Save data on DataFrame
    c_pf.savedf()

    # Extract Data
    df_net = c_pf.df_net

    # Save networks results on Excel
    c_pf.write_excel(filename=filename_DA, sheet_name='ppeer_kw', data=df_net['ppeer_df'])
    c_pf.write_excel(filename=filename_DA, sheet_name='qpeer_kvar', data=df_net['qpeer_df'])
    c_pf.write_excel(filename=filename_DA, sheet_name='vmpeer', data=df_net['vmpeer_df'])
    c_pf.write_excel(filename=filename_DA, sheet_name='pLoad', data=df_net['pLoad_df'])
    c_pf.write_excel(filename=filename_DA, sheet_name='pGen', data=df_net['pGen_df'])
    c_pf.write_excel(filename=filename_DA, sheet_name='pStore', data=df_net['pStore_df'])
    c_pf.write_excel(filename=filename_DA, sheet_name='pVeicolo', data=df_net['pVeicolo_df'])
    c_pf.write_excel(filename=filename_DA, sheet_name='SoC_storage', data=df_net['SoC_df'])
    c_pf.write_excel(filename=filename_DA, sheet_name='Line Loading', data=df_net['line_df'])
    c_pf.write_excel(filename=filename_DA, sheet_name='Trafo Loading', data=df_net['trafo_df'])
    # Save networks results on Excel
    c_pf.write_excel(filename=filename_CDA, sheet_name='ppeer_kw', data=df_net['ppeer_df'])
    c_pf.write_excel(filename=filename_CDA, sheet_name='qpeer_kvar', data=df_net['qpeer_df'])
    c_pf.write_excel(filename=filename_CDA, sheet_name='vmpeer', data=df_net['vmpeer_df'])
    c_pf.write_excel(filename=filename_CDA, sheet_name='pLoad', data=df_net['pLoad_df'])
    c_pf.write_excel(filename=filename_CDA, sheet_name='pGen', data=df_net['pGen_df'])
    c_pf.write_excel(filename=filename_CDA, sheet_name='pStore', data=df_net['pStore_df'])
    c_pf.write_excel(filename=filename_CDA, sheet_name='pVeicolo', data=df_net['pVeicolo_df'])
    c_pf.write_excel(filename=filename_CDA, sheet_name='SoC_storage', data=df_net['SoC_df'])
    c_pf.write_excel(filename=filename_CDA, sheet_name='Line Loading', data=df_net['line_df'])
    c_pf.write_excel(filename=filename_CDA, sheet_name='Trafo Loading', data=df_net['trafo_df'])
    # Save networks results on Excel
    c_pf.write_excel(filename=filename_PCDA, sheet_name='ppeer_kw', data=df_net['ppeer_df'])
    c_pf.write_excel(filename=filename_PCDA, sheet_name='qpeer_kvar', data=df_net['qpeer_df'])
    c_pf.write_excel(filename=filename_PCDA, sheet_name='vmpeer', data=df_net['vmpeer_df'])
    c_pf.write_excel(filename=filename_PCDA, sheet_name='pLoad', data=df_net['pLoad_df'])
    c_pf.write_excel(filename=filename_PCDA, sheet_name='pGen', data=df_net['pGen_df'])
    c_pf.write_excel(filename=filename_PCDA, sheet_name='pStore', data=df_net['pStore_df'])
    c_pf.write_excel(filename=filename_PCDA, sheet_name='pVeicolo', data=df_net['pVeicolo_df'])
    c_pf.write_excel(filename=filename_PCDA, sheet_name='SoC_storage', data=df_net['SoC_df'])
    c_pf.write_excel(filename=filename_PCDA, sheet_name='Line Loading', data=df_net['line_df'])
    c_pf.write_excel(filename=filename_PCDA, sheet_name='Trafo Loading', data=df_net['trafo_df'])

    # Save Users and addresses on Excel
    c_pf.write_excel(filename=filename_DA,
                     sheet_name='User addresses',
                     data={'address': m_da.k_addrs, 'node': [m_da.list_p[k].node for k in m_da.list_p.keys()]})

    eval_class_DA = ef.eval(m_da.contracts, buyGrid, sellGrid, m_da.list_p, m_da.list_p[list(m_da.list_p.keys())[0]].add, c_pf)
    eval_class_DA.evalSW(False)
    eval_class_DA.evalCQR(False)
    eval_class_DA.writexlsx(filename=filename_DA, sheet_name='Comparison SW', data=eval_class_DA.SW)
    eval_class_DA.writexlsx(filename=filename_DA, sheet_name='Comparison DW', data=eval_class_DA.DW)
    eval_class_DA.writexlsx(filename=filename_DA, sheet_name='Comparison CQR', data=eval_class_DA.CQR)
    eval_class_DA.writexlsx(filename=filename_DA, sheet_name='Comparison tot bid', data=eval_class_DA.tot_bid)

    # CDA
    c_pf.write_excel(filename=filename_CDA,
                     sheet_name='User addresses',
                     data={'address': m_cda.Participant.keys(),
                           'node': [m_cda.Participant[k].node for k in m_cda.Participant.keys()]})

    eval_class_CDA = ef.eval(m_cda.Contract, buyGrid, sellGrid, m_cda.Participant, m_cda.master.add, c_pf)
    eval_class_CDA.evalSW(True)
    eval_class_CDA.evalCQR(True)
    eval_class_CDA.writexlsx(filename=filename_CDA, sheet_name='Comparison SW', data=eval_class_CDA.SW)
    eval_class_CDA.writexlsx(filename=filename_CDA, sheet_name='Comparison DW', data=eval_class_CDA.DW)
    eval_class_CDA.writexlsx(filename=filename_CDA, sheet_name='Comparison CQR', data=eval_class_CDA.CQR)
    eval_class_CDA.writexlsx(filename=filename_CDA, sheet_name='Comparison tot bid', data=eval_class_CDA.tot_bid)

    # PCDA
    c_pf.write_excel(filename=filename_PCDA,
                     sheet_name='User addresses',
                     data={'address': m_pcda.Participant.keys(),
                           'node': [m_pcda.Participant[k].node for k in m_pcda.Participant.keys()]})

    eval_class_PCDA = ef.eval(m_pcda.Contract, buyGrid, sellGrid, m_pcda.Participant, m_pcda.master.add, c_pf)
    eval_class_PCDA.evalSW(True)
    eval_class_PCDA.evalCQR(True)
    eval_class_PCDA.writexlsx(filename=filename_PCDA, sheet_name='Comparison SW', data=eval_class_PCDA.SW)
    eval_class_PCDA.writexlsx(filename=filename_PCDA, sheet_name='Comparison DW', data=eval_class_PCDA.DW)
    eval_class_PCDA.writexlsx(filename=filename_PCDA, sheet_name='Comparison CQR', data=eval_class_PCDA.CQR)
    eval_class_PCDA.writexlsx(filename=filename_PCDA, sheet_name='Comparison tot bid', data=eval_class_PCDA.tot_bid)
