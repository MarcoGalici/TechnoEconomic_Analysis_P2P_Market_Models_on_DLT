# For PTDFs calculation
# Libraries
import pandapower as pp
import pandapower.networks as ppnet
import pandas as pd

from Networks import setPPnet as ppn
from Networks import readNet as rnet
import pandapower.pypower.makePTDF as PTDF
from pandapower.pd2ppc import _pd2ppc, _ppc2ppci


def createPTDF(netname):
    # Load network from file
    net = rnet.Net(netname)
    ppNet_class = ppn.PPnet(net)
    # Extract pandapower network
    pp_network = ppNet_class.emptyNet
    # Run pf
    pp.runpp(pp_network)
    # Converto into matpower format (in other words: no more dataframe but only matrix)
    ppc, ppci = _pd2ppc(pp_network)

    #In this case the branches and trafos are integrated into ppci['branch']
    ptdf = PTDF.makePTDF(ppci['baseMVA'], ppci['bus'], ppci['branch'])

    ptdf_table = pd.DataFrame(ptdf)

    PTDF_Test=ptdf_table.round(2)

    return ptdf, ptdf_table, PTDF_Test


if __name__ == "__main__":
    netname = "16nodi.dat"
    ptdf, ptdf_table, PTDF_Test = createPTDF(netname)
    print(ptdf)
    print(' ')
    print(ptdf_table)
    print(' ')
    print(PTDF_Test)