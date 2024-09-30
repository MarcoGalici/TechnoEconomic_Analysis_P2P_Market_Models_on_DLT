from Networks import readNet as rnet
from Networks import setPPnet as ppnet
import pandapower as pp
import copy as cp
import pandas as pd
from os.path import exists
import math
import numpy as np


def _storage(i, t, pp_net, cons, prod, dt, soc, pw_st):
    ### ONLY STORAGE ###
    # Capacità nominale della batteria
    cap = pp_net.storage.at[i, "max_e_mwh"]
    # Capacità Max
    # Mettiamo 0.9 perché il modello di storage di PandaPower non ha il parametro Capacità Nominale [kWh],
    # quindi usiamo "max_e_mwh" come parametro per mettere la capacità nominale
    cap_max = cap * 0.9
    # Capacità Min
    cap_min = pp_net.storage.at[i, "min_e_mwh"]
    # Check inital state of charge
    if t == 0:
        soc_init = pp_net.storage.at[i, "soc_percent"] * cap
    else:
        soc_init = soc['Storage'][i][-1]

    # Eval. consumption/injection of storage for this interval "t"
    diff = (prod - cons)
    pw_storage, soc_fin = setStorageProfile(diff, cap_max, cap_min, soc_init, dt)
    # Aggiorna stato di carica
    soc['Storage'][i].append(soc_fin)
    pw_st['Storage'][i].append(pw_storage)
    # Modifica consumption/injection of power for storage
    pp_net.storage.at[i, "p_mw"] = pw_storage

    return pp_net, soc, pw_st


def _ev(i, t, ev, typeEV, pp_net, dt, soc, pw_st):
    ### ONLY ELECTRIC VEHICLE ###
    pp_net.storage.at[i, "p_mw"] = pp_net.storage.at[i, "p_mw"] * ev[int(typeEV[i]) - 1][t]
    battCap = pp_net.storage.at[i, "max_e_mwh"]
    min_soc = 0.1 * battCap
    max_soc = 0.9 * battCap

    if pp_net.storage.at[i, "p_mw"] != 0:
        # VEHICLE PLUGGED
        # State of Charge of the Vehicle
        if t == 0:
            # Lo stato di carica iniziale sarà estratto da una distribuzione uniforme
            # tra il valore di min_soc e max_soc
            soc_init = np.random.uniform(low=min_soc, high=max_soc, size=1)[0]
            soc['EV'][i].append(soc_init)
        else:
            dP_ev, soc_aft = setEVprofile(soc['EV'][i][-1], min_soc, max_soc, pp_net.storage.at[i, "p_mw"], dt)
            soc['EV'][i].append(soc_aft)
            pw_st['EV'][i].append(dP_ev)
    else:
        # VEHICLE UNPLUGGED
        # Consumption - extracted randomly
        mu, sigma = 0.2, 0.1
        C = abs(np.random.normal(loc=mu, scale=sigma, size=1)[0]) * 1e-3
        # Distance - extracted randomly
        mu, sigma = 30, 5
        D = np.random.normal(loc=mu, scale=sigma, size=1)[0]
        # Stato di carica
        soc['EV'][i].append(soc['EV'][i][-1] - D * C)
        if soc['EV'][i][-1] < min_soc:
            soc['EV'][i][-1] = min_soc
        dP_ev = (soc['EV'][i][-1] - soc['EV'][i][-2]) / dt
        pw_st['EV'][i].append(dP_ev)

    return pp_net, soc, pw_st


def setStorageProfile(diff, cap_max, cap_min, cap, dt):
    soc = 0
    dP = 0
    # Charge
    if diff > 0:
        # La massima energia di Carica possibile
        E_charge = diff * dt

        if cap + E_charge < cap_max:
            # Posso ancora caricare
            dP = E_charge / dt
            soc = cap + E_charge

        elif cap + E_charge > cap_max:
            # La carica andrebbe oltre la cap_max, uso una carica ridotta
            E_charge_ridotta = (cap_max - cap) * dt
            dP = E_charge_ridotta / dt
            soc = cap + E_charge_ridotta

        elif cap == cap_max:
            # Non posso più Caricare
            dP = 0
            soc = cap

    # Discharge
    elif diff <= 0:
        # La massima energia di Scarica possibile
        E_discharge = diff * dt

        if cap - E_discharge > cap_min:
            # Posso ancora scaricare
            dP = E_discharge / dt
            soc = cap + E_discharge

        elif (cap - E_discharge) < cap_min:
            # La scarica andrebbe oltre la cap_min, uso una scarica ridotta
            E_discharge_ridotta = (cap_min - cap) * dt
            dP = E_discharge_ridotta / dt
            soc = cap + E_discharge_ridotta

        elif cap == cap_min:
            # Non posso più Scaricare
            dP = 0
            soc = cap

    return dP, soc


def setEVprofile(cap, min_soc, max_soc, pw, dt):
    soc = 0
    dP = 0
    # Charge
    if pw >= 0:
        # La massima energia di Carica possibile
        E_charge = pw * dt

        if cap + E_charge < max_soc:
            # Posso ancora caricare
            dP = E_charge / dt
            soc = cap + E_charge

        elif cap + E_charge > max_soc:
            # La carica andrebbe oltre la cap_max, uso una carica ridotta
            E_charge_ridotta = (max_soc - cap) * dt
            dP = E_charge_ridotta / dt
            soc = cap + E_charge_ridotta

        elif cap == max_soc:
            # Non posso più Caricare
            dP = 0
            soc = cap

    # Discharge
    elif pw < 0:
        # La massima energia di Scarica possibile
        E_discharge = pw * dt

        if cap - E_discharge > min_soc:
            # Posso ancora scaricare
            dP = E_discharge / dt
            soc = cap + E_discharge

        elif (cap - E_discharge) < min_soc:
            # La scarica andrebbe oltre la cap_min, uso una scarica ridotta
            E_discharge_ridotta = (min_soc - cap) * dt
            dP = E_discharge_ridotta / dt
            soc = cap + E_discharge_ridotta

        elif cap == min_soc:
            # Non posso più Scaricare
            dP = 0
            soc = cap

    return dP, soc


def setParameters(pp_net, profiles, types, t, dt, soc, pw_st):
    loads = profiles['Loads']
    gens = profiles['Gens']
    ev = profiles['EV']
    typeL = types['Loads']
    typeG = types['Gens']
    typeEV = types['EV']

    # LOADS
    for i in range(len(pp_net.load)):
        pp_net.load.at[i, "p_mw"] = pp_net.load.at[i, "p_mw"] * loads[int(typeL[i]) - 1][t]
        pp_net.load.at[i, "q_mvar"] = pp_net.load.at[i, "q_mvar"] * loads[int(typeL[i]) - 1][t]

    # GENERATORS
    typeG = [k for k in typeG if k != 0]
    for i in range(len(pp_net.gen)):
        pp_net.gen.at[i, "p_mw"] = pp_net.gen.at[i, "p_mw"] * gens[int(typeG[i]) - 1][t]

    # STORAGES & ELECTRIC VEHICLES
    # Verifichiamo la presenza dei Veicoli Elettrici
    member_node = list(pp_net.storage.name)
    index_ev = [member_node.index(list(filter(lambda x: 'EV' in x, pp_net.storage.name))[_idx])
                for _idx in range(len(list(filter(lambda x: 'EV' in x, pp_net.storage.name))))]
    for i in range(len(pp_net.storage)):
        if not(math.isnan(pp_net.storage.soc_percent[i])):
            # Consumo
            cons = pp_net.load.at[i, "p_mw"]
            # Produzione
            prod = pp_net.gen.at[i, "p_mw"]

            if len(index_ev) == 0:
                # Only Storage
                pp_net, soc, pw_st = _storage(i, t, pp_net, cons, prod, dt, soc, pw_st)
            else:
                # Storage + EV
                if i in index_ev:
                    pp_net, soc, pw_st = _ev(i, t, ev, typeEV, pp_net, dt, soc, pw_st)
                else:
                    pp_net, soc, pw_st = _storage(i, t, pp_net, cons, prod, dt, soc, pw_st)
        else:
            # Only EV
            pp_net, soc, pw_st = _ev(i, t, ev, typeEV, pp_net, dt, soc, pw_st)

    return pp_net, soc, pw_st


def setMatrix(A):
    idx = 0
    B = []
    for i in A.keys():
        if i != 'Dev. Stand. [p.u.]':
            B.append(A[i])
            idx += 1
    return B


def setProfile(net):
    # Estrai i profili dei carichi, generatori e EV
    profileL = setMatrix(net.DatiCurveGiornaliereDefault['Loads'])
    profileG = setMatrix(net.DatiCurveGiornaliereDefault['Gens'])
    profileEV = setMatrix(net.DatiCurveGiornaliereDefault['EV'])

    profiles = dict()
    profiles['Loads'] = profileL
    profiles['Gens'] = profileG
    profiles['EV'] = profileEV

    type = setMatrix(net.DatiReteDistribuzione['Nodi MT'])
    typeL = type[list(net.DatiReteDistribuzione['Nodi MT'].keys()).index('Tipologia C')]
    typeG = type[list(net.DatiReteDistribuzione['Nodi MT'].keys()).index('Tipologia G')]
    typeEV = type[list(net.DatiReteDistribuzione['Nodi MT'].keys()).index('Tipologia S')]

    types = dict()
    types['Loads'] = typeL
    types['Gens'] = typeG
    types['EV'] = typeEV

    return profiles, types


def setPeerStorage(pp_net):
    """ Set Storage for peers (only for those who have availability of storage) """
    soc = dict()
    soc['Storage'] = dict()
    soc['EV'] = dict()
    pw_st = dict()
    pw_st['Storage'] = dict()
    pw_st['EV'] = dict()
    for i in range(len(pp_net.storage)):
        if not(math.isnan(pp_net.storage.soc_percent[i])):
            soc['Storage'][i] = list()
            pw_st['Storage'][i] = list()
        else:
            soc['EV'][i] = list()
            pw_st['EV'][i] = list()

    return soc, pw_st


def runPPntime(network, t, profiles, types, vm, p_kw, q_kvar, soc, pw_st, dt):
    """Run Power Flow N times"""
    net, soc, pw_st = setParameters(network, profiles, types, t, dt, soc, pw_st)

    # print("interval: ", t)
    # print(net.storage.p_mw, net.storage.max_e_mwh, net.storage.min_e_mwh)
    # print(soc[0])
    # print(" ")
    # print(net.load.iloc[0])
    # print(" ")
    # print(net.gen.iloc[0])
    # print(" ")
    # print(" ")
    # print(" ")
    # exit()

    pp.runpp(net)

    vm[t] = net.res_bus.vm_pu
    p_kw[t] = net.res_bus.p_mw * 1e3
    q_kvar[t] = net.res_bus.q_mvar * 1e3

    return vm, p_kw, q_kvar, soc, pw_st


def write_excel(filename, sheet_name, data):
    """Trasforma un dizionario in un dataframe e scrivi i valori dentro un file excel"""

    df1 = pd.DataFrame.from_dict(data)
    # print(df1)
    file_exists = exists(filename)
    if file_exists:
        with pd.ExcelWriter(filename, engine='openpyxl', mode='a') as writer:
                df1.to_excel(writer, sheet_name=sheet_name)
    else:
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df1.to_excel(writer, sheet_name=sheet_name)


if __name__ == "__main__":
    # Load network from files
    net = rnet.Net('LV_16nodi.dat')

    # Create PandaPower network from files
    ppNet_class = ppnet.PPnet(net)

    # Extract PandaPower network
    pp_network = ppNet_class.emptyNet

    profiles, types = setProfile(net)

    # Definisce il tempo di ogni intervallo temporale
    T = len(profiles['Gens'][0])
    dt = 24/T

    # Set Storage for peers (only for those who have availability of storage)
    soc, pw_st = setPeerStorage(pp_network)

    # Esegui power flow T volte
    vm = dict()
    p_kw = dict()
    q_kvar = dict()
    for t in range(T):
        grid = cp.deepcopy(pp_network)
        vm, p_kw, q_kvar, soc, pw_st = runPPntime(grid, t, profiles, types, vm, p_kw, q_kvar, soc, pw_st, dt)

    print(pp_network)
    # print(p_kw[0], len(p_kw[0]), p_kw.keys())
    # print('Storage soc: ', soc['Storage'])
    # print(' ')
    # print('EV soc: ', soc['EV'])
    # print(' ')
    # print('Storage power: ', pw_st['Storage'])
    # print(' ')
    # print('EV power: ', pw_st['EV'])
    # print(' ')

    for k in range(len(pp_network.bus)):
        print('Node ' + str(k))
        print([p_kw[index][k] for index in p_kw.keys()])
        print(' ')
    # print(' ')
    # print([p_kw[index][2] for index in p_kw.keys()])

    # print(pp_network.storage)
    # print(pp_network.storage.min_e_mwh)

    # write_excel('res.xlsx', 'p_kw', p_kw)
