class Net:
    def __init__(self, networkName):
        self.nameParameters = ['--- PERIODO DI STUDIO ---',
                               '--- PARAMETRI ECONOMICI ---',
                               '--- VINCOLI TECNICI E TOPOLOGICI ---',
                               '--- COSTI UNITARI ---',
                               '--- DATI AFFIDABILISTICI STAZIONI AT/MT ---',
                               '--- DATI TECNICI E COSTI DEI DISPOSITIVI ---',
                               '--- DATI TECNICI, ECONOMICI ED AFFIDABILISTICI LINEE IN CAVO ---',
                               '--- DATI TECNICI, ECONOMICI ED AFFIDABILISTICI LINEE AEREE ---',
                               "--- INDICATORI QUALITA' DEL SERVIZIO ---",
                               '--- PARAMETRI PER ANALISI BUCHI DI TENSIONE ---',
                               '--- DATI GENERATORI ---',
                               '--- DATI RETE DI TRASMISSIONE ---',
                               '--- COSTI RETE ATTIVA ---',
                               '--- DATI TRASFORMATORI ---',
                               '--- DATI CURVE GIORNALIERE DI DEFAULT ---',
                               '--- DATI RETE DI DISTRIBUZIONE ---']
        self.PeriodoDiStudio = dict()
        self.ParametriEconomici = dict()
        self.VincoliTecniciTopologici = dict()
        self.CostiUnitari = dict()
        self.DatiAffidabilisticiStazioniMTAT = dict()
        self.DatiTecniciCostiDispositivi = dict()
        self.DatiTecniciEconomiciAffidabilisticiLineeCavo = dict()
        self.DatiTecniciEconomiciAffidabilisticiLineeAeree = dict()
        self.IndicatoriQualitaServizio = dict()
        self.ParametriAnalisiBuchiTensione = dict()
        self.DatiGeneratori = dict()
        self.DatiReteTrasmissione = dict()
        self.CostiReteAttiva = dict()
        self.DatiTrasformatori = dict()
        self.DatiCurveGiornaliereDefault = dict()
        self.DatiReteDistribuzione = dict()
        self.fillDict(networkName)

    def loadNet(self, net_name):
        file = open(net_name, 'r')
        lines = file.readlines()
        # print(lines)
        return lines

    def fillDict(self, net_name):
        content = self.loadNet(net_name)
        idx = 0
        icounter = 0
        for value in content:
            value = self.adaptValue(value)
            # print("value", value, idx)

            if value:
                self.fillDictionary(value, idx, icounter)
                icounter += 1
            else:
                idx += 1
                icounter = 0
                continue

            # if idx >= 24:
                # print(' ')
                # print('Periodo di studio: ', self.PeriodoDiStudio)
                # print('Parametri economici: ', self.ParametriEconomici)
                # print('Vincoli Tecnici Topologici: ', self.VincoliTecniciTopologici)
                # print('Costi Unitari: ', self.CostiUnitari)
                # print('Dati Aff. Stazioni MT/AT: ', self.DatiAffidabilisticiStazioniMTAT)
                # print('Dati tecnici costi dispositivi: ', self.DatiTecniciCostiDispositivi)
                # print('Dati tecnici economici Aff Linee Cavo: ', self.DatiTecniciEconomiciAffidabilisticiLineeCavo)
                # print('Dati tecnici economici Aff Linee Aeree: ', self.DatiTecniciEconomiciAffidabilisticiLineeAeree)
                # print('Indicatori qualità del servizio: ', self.IndicatoriQualitaServizio)
                # print('Analisi Buchi di tensione: ', self.ParametriAnalisiBuchiTensione)
                # print('Dati generatori: ', self.DatiGeneratori)
                # print('Rete trasmissione: ', self.DatiReteTrasmissione)
                # print('Costi rete attiva: ', self.CostiReteAttiva)
                # print('Trasformatori: ', self.DatiTrasformatori)
                # print('Curve Giornaliere default: ', self.DatiCurveGiornaliereDefault)
                # print('Rete di Distribuzione: ', self.DatiReteDistribuzione)
                #break

        # return False

    def fillList(self, _value, _idx, _icount):
        if _idx >= 21 and _icount >= 1:
            lista = dict()
            lista['float'] = list()
            lista['string'] = list()
            for val in _value:
                try:
                    lista['float'].append(float(val))
                except ValueError:
                    lista['string'].append(val)
        else:
            try:
                try:
                    lista = [float(val) for val in _value]
                except ValueError:
                    lista = [float(val) for val in _value[1:len(_value)]]
            except ValueError:
                lista = []
        return lista

    def adaptValue(self, _value):
        """Eliminiamo da ogni riga i termini:
               * ';'
               * spazi vuoti nella stringa
               * elementi vuoti nella lista"""
        _value = _value.split(';')
        _value = [index.strip() for index in _value]
        try:
            # value.remove('')
            _value = list(filter(None, _value))
        except ValueError:
            pass
        return _value

    def fillDictionary(self, _row_list, _idx, _icount):
        """Riempiamo ogni dizionario con i valori corretti"""
        listValue = self.fillList(_row_list, _idx, _icount)

        # Periodo di Studio
        if _idx == 0:
            if _icount == 1:
                self.PeriodoDiStudio['Inizio Studio'] = listValue[0]
                self.PeriodoDiStudio['Fine Studio'] = listValue[1]
            elif _icount == 2:
                self.PeriodoDiStudio['Numero sottoperiodi studio'] = listValue[0]
            elif _icount == 3:
                for n_periodi in range(int(self.PeriodoDiStudio['Numero sottoperiodi studio'])):
                    self.PeriodoDiStudio['Inizio Sottoperiodo ' + str(n_periodi + 1)] = listValue[n_periodi]
        # Parametri Economici
        elif _idx == 1:
            if _icount == 1:
                self.ParametriEconomici['Tasso di Interesse Annuo [%]'] = listValue[0]
            elif _icount == 2:
                self.ParametriEconomici['Tasso di Inflazione Annuo [%]'] = listValue[0]
        # Vincoli Tecnici Topologici
        elif _idx == 2:
            if _icount == 2:
                self.VincoliTecniciTopologici['Numero massimo connessioni'] = dict()
                self.VincoliTecniciTopologici['Numero massimo connessioni']['Nodo TOP'] = listValue[0]
                self.VincoliTecniciTopologici['Numero massimo connessioni']['Nodo LAT'] = listValue[1]
            elif _icount == 4:
                self.VincoliTecniciTopologici['Max c.d.t. Ammissibile [%]'] = dict()
                self.VincoliTecniciTopologici['Max c.d.t. Ammissibile [%]']['Normale'] = listValue[0]
                self.VincoliTecniciTopologici['Max c.d.t. Ammissibile [%]']['Emergenza'] = listValue[1]
                self.VincoliTecniciTopologici['Max c.d.t. Ammissibile [%]']['Prob min evento'] = listValue[2]
            elif _icount == 5:
                self.VincoliTecniciTopologici['Max sovratensione Ammissibile [%]'] = dict()
                self.VincoliTecniciTopologici['Max sovratensione Ammissibile [%]']['Normale'] = listValue[0]
                self.VincoliTecniciTopologici['Max sovratensione Ammissibile [%]']['Emergenza'] = listValue[1]
                self.VincoliTecniciTopologici['Max sovratensione Ammissibile [%]']['Prob min evento'] = listValue[2]
            elif _icount == 6:
                self.VincoliTecniciTopologici['Max sovraccarico ammesso [%]'] = dict()
                self.VincoliTecniciTopologici['Max sovraccarico ammesso [%]']['Emergenza'] = listValue[0]
                self.VincoliTecniciTopologici['Max sovraccarico ammesso [%]']['Prob min evento'] = listValue[1]
        # Costi Unitari
        elif _idx == 3:
            if _icount == 1:
                self.CostiUnitari['Costo Unitario delle Perdite [euro/kWh]'] = listValue[0]
            elif _icount == 2:
                self.CostiUnitari["Costo Unitario dell'Energia non Fornita [euro/kWh]"] = listValue[0]
        # Dati Affidabilistici Stazioni AT/MT
        elif _idx == 4:
            if _icount == 2:
                self.DatiAffidabilisticiStazioniMTAT['Sottostazione AT/MT Urbana'] = dict()
                self.DatiAffidabilisticiStazioniMTAT['Sottostazione AT/MT Urbana']['Vita [anni]'] = listValue[0]
                self.DatiAffidabilisticiStazioniMTAT['Sottostazione AT/MT Urbana']['N. guasti trafo'] = listValue[1]
                self.DatiAffidabilisticiStazioniMTAT['Sottostazione AT/MT Urbana']['Trip guasti trafo [h]'] = listValue[2]
                self.DatiAffidabilisticiStazioniMTAT['Sottostazione AT/MT Urbana']['N. annuo FSC'] = listValue[3]
                self.DatiAffidabilisticiStazioniMTAT['Sottostazione AT/MT Urbana']['Trip FSC [h]'] = listValue[4]
            elif _icount == 3:
                self.DatiAffidabilisticiStazioniMTAT['Sottostazione AT/MT Rurale'] = dict()
                self.DatiAffidabilisticiStazioniMTAT['Sottostazione AT/MT Rurale']['Vita [anni]'] = listValue[0]
                self.DatiAffidabilisticiStazioniMTAT['Sottostazione AT/MT Rurale']['N. guasti trafo'] = listValue[1]
                self.DatiAffidabilisticiStazioniMTAT['Sottostazione AT/MT Rurale']['Trip guasti trafo [h]'] = listValue[2]
                self.DatiAffidabilisticiStazioniMTAT['Sottostazione AT/MT Rurale']['N. annuo FSC'] = listValue[3]
                self.DatiAffidabilisticiStazioniMTAT['Sottostazione AT/MT Rurale']['Trip FSC [h]'] = listValue[4]
        # Dati Tecnici Costi Dispositivi
        elif _idx == 5:
            if _icount == 2:
                self.DatiTecniciCostiDispositivi['Dynamic Voltage Restorer'] = dict()
                self.DatiTecniciCostiDispositivi['Dynamic Voltage Restorer']['Costo [euro/kW]'] = listValue[0]
                self.DatiTecniciCostiDispositivi['Dynamic Voltage Restorer']['Vita [anni]'] = listValue[1]
            elif _icount == 4:
                self.DatiTecniciCostiDispositivi['Automatismi'] = dict()
                self.DatiTecniciCostiDispositivi['Automatismi']['Costo [euro/kW]'] = listValue[0]
                self.DatiTecniciCostiDispositivi['Automatismi']['Vita [anni]'] = listValue[1]
            elif _icount == 6:
                self.DatiTecniciCostiDispositivi['Vita Media degli Interruttori [Anni]'] = listValue[0]
            elif _icount == 7:
                self.DatiTecniciCostiDispositivi['N taglie interruttori previste'] = listValue[0]
                self.DatiTecniciCostiDispositivi['Taglia interruttore'] = dict()
                self.DatiTecniciCostiDispositivi['Taglia interruttore']['P.I. [kA]'] = list()
                self.DatiTecniciCostiDispositivi['Taglia interruttore']['Costo [keuro]'] = list()
            elif _icount >= 9:
                self.DatiTecniciCostiDispositivi['Taglia interruttore']['P.I. [kA]'].append(listValue[0])
                self.DatiTecniciCostiDispositivi['Taglia interruttore']['Costo [keuro]'].append(listValue[1])
        # Dati Tecnici Economici Affidabilistici Linee Cavo
        elif _idx == 6:
            if _icount == 0:
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo'] = dict()
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Normalizzati'] = 0
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Non normalizzati'] = 0
            if _icount == 2:
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Normalizzati'] = listValue[0]
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Non normalizzati'] = listValue[1]

                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Normalizzato'] = dict()
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Normalizzato']['N'] = list()
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Normalizzato']['S[mmq]'] = list()
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Normalizzato']['R[Ohm/km]'] = list()
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Normalizzato']['X[Ohm/km]'] = list()
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Normalizzato']['C[microF/km]'] = list()
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Normalizzato']['Portata [A]'] = list()

                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Non Normalizzato'] = dict()
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Non Normalizzato']['N'] = list()
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Non Normalizzato']['S[mmq]'] = list()
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Non Normalizzato']['R[Ohm/km]'] = list()
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Non Normalizzato']['X[Ohm/km]'] = list()
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Non Normalizzato']['C[microF/km]'] = list()
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Non Normalizzato']['Portata [A]'] = list()
            elif 4 <= _icount < 4+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Normalizzati']:
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Normalizzato']['N'].append(listValue[0])
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Normalizzato']['S[mmq]'].append(listValue[1])
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Normalizzato']['R[Ohm/km]'].append(listValue[2])
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Normalizzato']['X[Ohm/km]'].append(listValue[3])
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Normalizzato']['C[microF/km]'].append(listValue[4])
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Normalizzato']['Portata [A]'].append(listValue[5])
            elif 4+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Normalizzati'] <= _icount < 4+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Non normalizzati']:
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Non Normalizzato']['N'].append(listValue[0])
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Non Normalizzato']['S[mmq]'].append(listValue[1])
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Non Normalizzato']['R[Ohm/km]'].append(listValue[2])
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Non Normalizzato']['X[Ohm/km]'].append(listValue[3])
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Non Normalizzato']['C[microF/km]'].append(listValue[4])
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Conduttore Cavo Non Normalizzato']['Portata [A]'].append(listValue[5])
            elif 4+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Non normalizzati'] <= _icount < 4+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Non normalizzati']+1:
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Sezione minima cavo [mmq]'] = listValue[0]
            elif 4+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Non normalizzati']+1 <= _icount < 4+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Non normalizzati']+2:
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Vita Media [Anni]'] = listValue[0]
            elif 4+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Non normalizzati']+2 <= _icount < 4+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Non normalizzati']+3:
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Coefficiente di Tortuosita'] = listValue[0]
            elif 4+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Non normalizzati']+4 <= _icount < 4+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Non normalizzati']+5:
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Costi'] = dict()
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Costi']['Fisso [keuro/km]'] = listValue[0]
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Costi']['variabile [euro/km*mmq]'] = listValue[1]
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Costi']['fisso scavi [euro/km]'] = listValue[2]
            elif 4+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Non normalizzati']+5 <= _icount < 4+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Non normalizzati']+6:
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Numero Annuo di Guasti per 100 Km di Linea'] = listValue[0]
            elif 4+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Non normalizzati']+6 <= _icount < 4+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Non normalizzati']+7:
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tempo Medio di Riparazione dei Guasti [h]'] = listValue[0]
            elif 4+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Non normalizzati']+8 <= _icount < 4+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tipi di Conduttore Cavo']['Non normalizzati']+9:
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tempo di Localizzazione del Guasto [h]'] = dict()
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tempo di Localizzazione del Guasto [h]']['senza auto'] = listValue[0]
                self.DatiTecniciEconomiciAffidabilisticiLineeCavo['Tempo di Localizzazione del Guasto [h]']['con auto'] = listValue[1]
        # Dati Tecnici Economici Affidabilistici Linee Aeree
        elif _idx == 7:
            if _icount == 0:
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo'] = dict()
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Normalizzati'] = 0
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Non normalizzati'] = 0
            if _icount == 2:
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Normalizzati'] = listValue[0]
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Non normalizzati'] = listValue[1]

                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Normalizzato'] = dict()
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Normalizzato']['N'] = list()
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Normalizzato']['S[mmq]'] = list()
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Normalizzato']['R[Ohm/km]'] = list()
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Normalizzato']['X[Ohm/km]'] = list()
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Normalizzato']['C[microF/km]'] = list()
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Normalizzato']['Portata [A]'] = list()

                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Non Normalizzato'] = dict()
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Non Normalizzato']['N'] = list()
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Non Normalizzato']['S[mmq]'] = list()
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Non Normalizzato']['R[Ohm/km]'] = list()
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Non Normalizzato']['X[Ohm/km]'] = list()
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Non Normalizzato']['C[microF/km]'] = list()
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Non Normalizzato']['Portata [A]'] = list()
            elif 4 <= _icount < 4+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Normalizzati']:
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Normalizzato']['N'].append(listValue[0])
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Normalizzato']['S[mmq]'].append(listValue[1])
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Normalizzato']['R[Ohm/km]'].append(listValue[2])
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Normalizzato']['X[Ohm/km]'].append(listValue[3])
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Normalizzato']['C[microF/km]'].append(listValue[4])
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Normalizzato']['Portata [A]'].append(listValue[5])
            elif 4+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Normalizzati'] <= _icount < 4+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Non normalizzati']:
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Non Normalizzato']['N'].append(listValue[0])
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Non Normalizzato']['S[mmq]'].append(listValue[1])
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Non Normalizzato']['R[Ohm/km]'].append(listValue[2])
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Non Normalizzato']['X[Ohm/km]'].append(listValue[3])
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Non Normalizzato']['C[microF/km]'].append(listValue[4])
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Conduttore Aereo Non Normalizzato']['Portata [A]'].append(listValue[5])
            elif 4+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Non normalizzati'] <= _icount < 4+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Non normalizzati']+1:
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Sezione minima linea aerea [mmq]'] = listValue[0]
            elif 4+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Non normalizzati']+1 <= _icount < 4+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Non normalizzati']+2:
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Vita Media [Anni]'] = listValue[0]
            elif 4+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Non normalizzati']+2 <= _icount < 4+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Non normalizzati']+3:
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Coefficiente di Tortuosita'] = listValue[0]
            elif 4+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Non normalizzati']+4 <= _icount < 4+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Non normalizzati']+5:
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Costi'] = dict()
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Costi']['Fisso [keuro/km]'] = listValue[0]
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Costi']['variabile [euro/km*mmq]'] = listValue[1]
            elif 4+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Non normalizzati']+5 <= _icount < 4+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Non normalizzati']+6:
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Numero Annuo di Guasti per 100 Km di Linea'] = listValue[0]
            elif 4+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Non normalizzati']+6 <= _icount < 4+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Non normalizzati']+7:
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tempo Medio di Riparazione dei Guasti [h]'] = listValue[0]
            elif 4+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Non normalizzati']+8 <= _icount < 4+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Normalizzati']+self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tipi di Conduttore Aereo']['Non normalizzati']+9:
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tempo di Localizzazione del Guasto [h]'] = dict()
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tempo di Localizzazione del Guasto [h]']['senza auto'] = listValue[0]
                self.DatiTecniciEconomiciAffidabilisticiLineeAeree['Tempo di Localizzazione del Guasto [h]']['con auto'] = listValue[1]
        # Indicatori Qualita Servizio
        elif _idx == 8:
            if _icount == 2:
                self.IndicatoriQualitaServizio['Interruzioni urbane'] = dict()
                self.IndicatoriQualitaServizio['Interruzioni urbane']['numero max'] = listValue[0]
                self.IndicatoriQualitaServizio['Interruzioni urbane']['durata max [min]'] = listValue[1]
            elif _icount == 3:
                self.IndicatoriQualitaServizio['Interruzioni rurali'] = dict()
                self.IndicatoriQualitaServizio['Interruzioni rurali']['numero max'] = listValue[0]
                self.IndicatoriQualitaServizio['Interruzioni rurali']['durata max [min]'] = listValue[1]
            elif _icount == 4:
                self.IndicatoriQualitaServizio['Min Prob Isola Intenzionale (GD > Carico) [%]'] = listValue[0]
        # Parametri Analisi Buchi Tensione
        elif _idx == 9:
            if _icount == 1:
                self.ParametriAnalisiBuchiTensione['Profondita critica del buco di tensione [% di Vn]'] = listValue[0]
            elif _icount == 3:
                self.ParametriAnalisiBuchiTensione['Frequenza limite [voltage dips/year]'] = dict()
                self.ParametriAnalisiBuchiTensione['Frequenza limite [voltage dips/year]']['Nodo TOP'] = listValue[0]
                self.ParametriAnalisiBuchiTensione['Frequenza limite [voltage dips/year]']['Nodo LAT'] = listValue[1]
            elif _icount == 5:
                self.ParametriAnalisiBuchiTensione['Numero guasti trifase permanenti [guasti/anno 100 km]'] = dict()
                self.ParametriAnalisiBuchiTensione['Numero guasti trifase permanenti [guasti/anno 100 km]']['aereo'] = listValue[0]
                self.ParametriAnalisiBuchiTensione['Numero guasti trifase permanenti [guasti/anno 100 km]']['cavo'] = listValue[1]
            elif _icount == 6:
                self.ParametriAnalisiBuchiTensione['Numero guasti bifase permanenti [guasti/anno 100 km]'] = dict()
                self.ParametriAnalisiBuchiTensione['Numero guasti bifase permanenti [guasti/anno 100 km]']['aereo'] = listValue[0]
                self.ParametriAnalisiBuchiTensione['Numero guasti bifase permanenti [guasti/anno 100 km]']['cavo'] = listValue[1]
            elif _icount == 7:
                self.ParametriAnalisiBuchiTensione['Numero guasti trifase transitori [guasti/anno 100 km]'] = dict()
                self.ParametriAnalisiBuchiTensione['Numero guasti trifase transitori [guasti/anno 100 km]']['aereo'] = listValue[0]
            elif _icount == 8:
                self.ParametriAnalisiBuchiTensione['Numero guasti bifase transitori [guasti/anno 100 km]'] = dict()
                self.ParametriAnalisiBuchiTensione['Numero guasti bifase transitori [guasti/anno 100 km]']['aereo'] = listValue[0]
            elif _icount == 9:
                self.ParametriAnalisiBuchiTensione['Numero guasti monofase transitori [guasti/anno 100 km]'] = dict()
                self.ParametriAnalisiBuchiTensione['Numero guasti monofase transitori [guasti/anno 100 km]']['aereo'] = listValue[0]
            elif _icount == 11:
                self.ParametriAnalisiBuchiTensione['Costo medio dei buchi di tensione [euro/Dip]'] = dict()
                self.ParametriAnalisiBuchiTensione['Costo medio dei buchi di tensione [euro/Dip]']['Nodo TOP'] = listValue[0]
                self.ParametriAnalisiBuchiTensione['Costo medio dei buchi di tensione [euro/Dip]']['Nodo LAT'] = listValue[1]
            elif _icount == 13:
                self.ParametriAnalisiBuchiTensione['Costo dei buchi di tensione per utenza [euro/Dip]'] = dict()
                self.ParametriAnalisiBuchiTensione['Costo dei buchi di tensione per utenza [euro/Dip]']['residenziale'] = listValue[0]
                self.ParametriAnalisiBuchiTensione['Costo dei buchi di tensione per utenza [euro/Dip]']['agricola'] = listValue[1]
                self.ParametriAnalisiBuchiTensione['Costo dei buchi di tensione per utenza [euro/Dip]']['industriale'] = listValue[2]
                self.ParametriAnalisiBuchiTensione['Costo dei buchi di tensione per utenza [euro/Dip]']['ill. pubblica'] = listValue[3]
                self.ParametriAnalisiBuchiTensione['Costo dei buchi di tensione per utenza [euro/Dip]']['terziario'] = listValue[4]
        # Dati Generatori
        elif _idx == 10:
            if _icount == 2:
                self.DatiGeneratori['Eolico'] = dict()
                self.DatiGeneratori['Eolico']['Costo energia [euro/kWh]'] = listValue[0]
                self.DatiGeneratori['Eolico']['Costo installazione [euro/kW]'] = listValue[1]
                self.DatiGeneratori['Eolico']['Costo esercizio [euro/kWh]'] = listValue[2]
                self.DatiGeneratori['Eolico']['Emissioni CO2 [kg/kWh]'] = listValue[3]
                self.DatiGeneratori['Eolico']['Isola intenzionale'] = listValue[4]
                self.DatiGeneratori['Eolico']['Regolazione di tensione'] = listValue[5]
                self.DatiGeneratori['Eolico']['Vita media [anni]'] = listValue[6]
            elif _icount == 3:
                self.DatiGeneratori['PV'] = dict()
                self.DatiGeneratori['PV']['Costo energia [euro/kWh]'] = listValue[0]
                self.DatiGeneratori['PV']['Costo installazione [euro/kW]'] = listValue[1]
                self.DatiGeneratori['PV']['Costo esercizio [euro/kWh]'] = listValue[2]
                self.DatiGeneratori['PV']['Emissioni CO2 [kg/kWh]'] = listValue[3]
                self.DatiGeneratori['PV']['Isola intenzionale'] = listValue[4]
                self.DatiGeneratori['PV']['Regolazione di tensione'] = listValue[5]
                self.DatiGeneratori['PV']['Vita media [anni]'] = listValue[6]
            elif _icount == 4:
                self.DatiGeneratori['FC'] = dict()
                self.DatiGeneratori['FC']['Costo energia [euro/kWh]'] = listValue[0]
                self.DatiGeneratori['FC']['Costo installazione [euro/kW]'] = listValue[1]
                self.DatiGeneratori['FC']['Costo esercizio [euro/kWh]'] = listValue[2]
                self.DatiGeneratori['FC']['Emissioni CO2 [kg/kWh]'] = listValue[3]
                self.DatiGeneratori['FC']['Isola intenzionale'] = listValue[4]
                self.DatiGeneratori['FC']['Regolazione di tensione'] = listValue[5]
                self.DatiGeneratori['FC']['Vita media [anni]'] = listValue[6]
            elif _icount == 5:
                self.DatiGeneratori['CHP'] = dict()
                self.DatiGeneratori['CHP']['Costo energia [euro/kWh]'] = listValue[0]
                self.DatiGeneratori['CHP']['Costo installazione [euro/kW]'] = listValue[1]
                self.DatiGeneratori['CHP']['Costo esercizio [euro/kWh]'] = listValue[2]
                self.DatiGeneratori['CHP']['Emissioni CO2 [kg/kWh]'] = listValue[3]
                self.DatiGeneratori['CHP']['Isola intenzionale'] = listValue[4]
                self.DatiGeneratori['CHP']['Regolazione di tensione'] = listValue[5]
                self.DatiGeneratori['CHP']['Vita media [anni]'] = listValue[6]
            elif _icount == 6:
                self.DatiGeneratori['Turbogas'] = dict()
                self.DatiGeneratori['Turbogas']['Costo energia [euro/kWh]'] = listValue[0]
                self.DatiGeneratori['Turbogas']['Costo installazione [euro/kW]'] = listValue[1]
                self.DatiGeneratori['Turbogas']['Costo esercizio [euro/kWh]'] = listValue[2]
                self.DatiGeneratori['Turbogas']['Emissioni CO2 [kg/kWh]'] = listValue[3]
                self.DatiGeneratori['Turbogas']['Isola intenzionale'] = listValue[4]
                self.DatiGeneratori['Turbogas']['Regolazione di tensione'] = listValue[5]
                self.DatiGeneratori['Turbogas']['Vita media [anni]'] = listValue[6]
        # Dati Rete di Trasmissione
        elif _idx == 11:
            if _icount == 1:
                self.DatiReteTrasmissione['Costo Energia [euro/kWh]'] = listValue[0]
            elif _icount == 2:
                self.DatiReteTrasmissione['Emissioni CO2 [kg/kWh]'] = listValue[0]
        # Costi Rete Attiva
        elif _idx == 12 or _idx == 13 or _idx == 14 or _idx == 15:
            if _icount == 0 and _idx == 12:
                self.CostiReteAttiva['Costi Generation Curtailment'] = dict()
                self.CostiReteAttiva['Costi Generation Curtailment']['Eolico'] = dict()
                self.CostiReteAttiva['Costi Generation Curtailment']['PV'] = dict()
                self.CostiReteAttiva['Costi Generation Curtailment']['FC'] = dict()
                self.CostiReteAttiva['Costi Generation Curtailment']['CHP'] = dict()
                self.CostiReteAttiva['Costi Generation Curtailment']['Turbogas'] = dict()

                self.CostiReteAttiva['Costi Demand Side Management'] = dict()
                self.CostiReteAttiva['Costi Demand Side Management']['Utenza residenziale'] = dict()
                self.CostiReteAttiva['Costi Demand Side Management']['Utenza agricola'] = dict()
                self.CostiReteAttiva['Costi Demand Side Management']['Utenza industriale'] = dict()
                self.CostiReteAttiva['Costi Demand Side Management']['Utenza ill. pubblica'] = dict()
                self.CostiReteAttiva['Costi Demand Side Management']['Utenza terziario'] = dict()

                self.CostiReteAttiva['Costi Regolazione di tensione'] = dict()
                self.CostiReteAttiva['Costi Regolazione di tensione']['Eolico'] = dict()
                self.CostiReteAttiva['Costi Regolazione di tensione']['PV'] = dict()
                self.CostiReteAttiva['Costi Regolazione di tensione']['FC'] = dict()
                self.CostiReteAttiva['Costi Regolazione di tensione']['CHP'] = dict()
                self.CostiReteAttiva['Costi Regolazione di tensione']['Turbogas'] = dict()
            elif _icount == 3 and _idx == 12:
                self.CostiReteAttiva['Costi Generation Curtailment']['Eolico']['Fisso disp cliente [euro/kW/anno]'] = listValue[0]
                self.CostiReteAttiva['Costi Generation Curtailment']['Eolico']['Variabile [euro/kWh]'] = listValue[1]
            elif _icount == 4 and _idx == 12:
                self.CostiReteAttiva['Costi Generation Curtailment']['PV']['Fisso disp cliente [euro/kW/anno]'] = listValue[0]
                self.CostiReteAttiva['Costi Generation Curtailment']['PV']['Variabile [euro/kWh]'] = listValue[1]
            elif _icount == 5 and _idx == 12:
                self.CostiReteAttiva['Costi Generation Curtailment']['FC']['Fisso disp cliente [euro/kW/anno]'] = listValue[0]
                self.CostiReteAttiva['Costi Generation Curtailment']['FC']['Variabile [euro/kWh]'] = listValue[1]
            elif _icount == 6 and _idx == 12:
                self.CostiReteAttiva['Costi Generation Curtailment']['CHP']['Fisso disp cliente [euro/kW/anno]'] = listValue[0]
                self.CostiReteAttiva['Costi Generation Curtailment']['CHP']['Variabile [euro/kWh]'] = listValue[1]
            elif _icount == 7 and _idx == 12:
                self.CostiReteAttiva['Costi Generation Curtailment']['Turbogas']['Fisso disp cliente [euro/kW/anno]'] = listValue[0]
                self.CostiReteAttiva['Costi Generation Curtailment']['Turbogas']['Variabile [euro/kWh]'] = listValue[1]
            elif _icount == 8 and _idx == 12:
                self.CostiReteAttiva['Costi Generation Curtailment']['Fisso infrastrutture [euro/gen]'] = listValue[0]
            elif _icount == 2 and _idx == 13:
                self.CostiReteAttiva['Costi Demand Side Management']['Utenza residenziale']['Fisso disp cliente [euro/kW/anno]'] = listValue[0]
                self.CostiReteAttiva['Costi Demand Side Management']['Utenza residenziale']['Variabile [euro/kWh]'] = listValue[1]
            elif _icount == 3 and _idx == 13:
                self.CostiReteAttiva['Costi Demand Side Management']['Utenza agricola']['Fisso disp cliente [euro/kW/anno]'] = listValue[0]
                self.CostiReteAttiva['Costi Demand Side Management']['Utenza agricola']['Variabile [euro/kWh]'] = listValue[1]
            elif _icount == 4 and _idx == 13:
                self.CostiReteAttiva['Costi Demand Side Management']['Utenza industriale']['Fisso disp cliente [euro/kW/anno]'] = listValue[0]
                self.CostiReteAttiva['Costi Demand Side Management']['Utenza industriale']['Variabile [euro/kWh]'] = listValue[1]
            elif _icount == 5 and _idx == 13:
                self.CostiReteAttiva['Costi Demand Side Management']['Utenza ill. pubblica']['Fisso disp cliente [euro/kW/anno]'] = listValue[0]
                self.CostiReteAttiva['Costi Demand Side Management']['Utenza ill. pubblica']['Variabile [euro/kWh]'] = listValue[1]
            elif _icount == 6 and _idx == 13:
                self.CostiReteAttiva['Costi Demand Side Management']['Utenza terziario']['Fisso disp cliente [euro/kW/anno]'] = listValue[0]
                self.CostiReteAttiva['Costi Demand Side Management']['Utenza terziario']['Variabile [euro/kWh]'] = listValue[1]
            elif _icount == 7 and _idx == 13:
                self.CostiReteAttiva['Costi Demand Side Management']['Fisso infrastrutture [euro/carico]'] = listValue[0]
            elif _icount == 2 and _idx == 14:
                self.CostiReteAttiva['Costi Regolazione di tensione']['Eolico']['Fisso disp cliente [euro/kW/anno]'] = listValue[0]
                self.CostiReteAttiva['Costi Regolazione di tensione']['Eolico']['Variabile [euro/kWh]'] = listValue[1]
            elif _icount == 3 and _idx == 14:
                self.CostiReteAttiva['Costi Regolazione di tensione']['PV']['Fisso disp cliente [euro/kW/anno]'] = listValue[0]
                self.CostiReteAttiva['Costi Regolazione di tensione']['PV']['Variabile [euro/kWh]'] = listValue[1]
            elif _icount == 4 and _idx == 14:
                self.CostiReteAttiva['Costi Regolazione di tensione']['FC']['Fisso disp cliente [euro/kW/anno]'] = listValue[0]
                self.CostiReteAttiva['Costi Regolazione di tensione']['FC']['Variabile [euro/kWh]'] = listValue[1]
            elif _icount == 5 and _idx == 14:
                self.CostiReteAttiva['Costi Regolazione di tensione']['CHP']['Fisso disp cliente [euro/kW/anno]'] = listValue[0]
                self.CostiReteAttiva['Costi Regolazione di tensione']['CHP']['Variabile [euro/kWh]'] = listValue[1]
            elif _icount == 6 and _idx == 14:
                self.CostiReteAttiva['Costi Regolazione di tensione']['Turbogas']['Fisso disp cliente [euro/kW/anno]'] = listValue[0]
                self.CostiReteAttiva['Costi Regolazione di tensione']['Turbogas']['Variabile [euro/kWh]'] = listValue[1]
            elif _icount == 7 and _idx == 14:
                self.CostiReteAttiva['Costi Regolazione di tensione']['Fisso infrastrutture [euro/carico]'] = listValue[0]
            elif _icount == 0 and _idx == 15:
                self.CostiReteAttiva['Costo dispositivo riconfigurazione on-line [keuro]'] = listValue[0]
        # Dati Trasformatore
        elif _idx == 16:
            if _icount == 0:
                self.DatiTrasformatori['Tipi di Trasformatori'] = dict()
                self.DatiTrasformatori['Tipi di Trasformatori']['Normalizzati'] = 0
                self.DatiTrasformatori['Tipi di Trasformatori']['Non normalizzati'] = 0

                self.DatiTrasformatori['Trasformatore Normalizzato'] = dict()
                self.DatiTrasformatori['Trasformatore Normalizzato']['N'] = list()
                self.DatiTrasformatori['Trasformatore Normalizzato']['Taglia [MVA]'] = list()
                self.DatiTrasformatori['Trasformatore Normalizzato']['Vcc [%]'] = list()
                self.DatiTrasformatori['Trasformatore Normalizzato']['P_vuoto [kW]'] = list()
                self.DatiTrasformatori['Trasformatore Normalizzato']['P_carico [kW]'] = list()

                self.DatiTrasformatori['Trasformatore Non Normalizzato'] = dict()
                self.DatiTrasformatori['Trasformatore Non Normalizzato']['N'] = list()
                self.DatiTrasformatori['Trasformatore Non Normalizzato']['Taglia [MVA]'] = list()
                self.DatiTrasformatori['Trasformatore Non Normalizzato']['Vcc [%]'] = list()
                self.DatiTrasformatori['Trasformatore Non Normalizzato']['P_vuoto [kW]'] = list()
                self.DatiTrasformatori['Trasformatore Non Normalizzato']['P_carico [kW]'] = list()
            elif _icount == 2:
                self.DatiTrasformatori['Tipi di Trasformatori']['Normalizzati'] = listValue[0]
                self.DatiTrasformatori['Tipi di Trasformatori']['Non normalizzati'] = listValue[1]
            elif 4 <= _icount < 4+self.DatiTrasformatori['Tipi di Trasformatori']['Normalizzati']:
                self.DatiTrasformatori['Trasformatore Normalizzato']['N'].append(listValue[0])
                self.DatiTrasformatori['Trasformatore Normalizzato']['Taglia [MVA]'].append(listValue[1])
                self.DatiTrasformatori['Trasformatore Normalizzato']['Vcc [%]'].append(listValue[2])
                self.DatiTrasformatori['Trasformatore Normalizzato']['P_vuoto [kW]'].append(listValue[3])
                self.DatiTrasformatori['Trasformatore Normalizzato']['P_carico [kW]'].append(listValue[4])
            elif 4+self.DatiTrasformatori['Tipi di Trasformatori']['Normalizzati'] <= _icount < 4+self.DatiTrasformatori['Tipi di Trasformatori']['Normalizzati']+self.DatiTrasformatori['Tipi di Trasformatori']['Non normalizzati']:
                self.DatiTrasformatori['Trasformatore Non Normalizzato']['N'].append(listValue[0])
                self.DatiTrasformatori['Trasformatore Non Normalizzato']['Taglia [MVA]'].append(listValue[1])
                self.DatiTrasformatori['Trasformatore Non Normalizzato']['Vcc [%]'].append(listValue[2])
                self.DatiTrasformatori['Trasformatore Non Normalizzato']['P_vuoto [kW]'].append(listValue[3])
                self.DatiTrasformatori['Trasformatore Non Normalizzato']['P_carico [kW]'].append(listValue[4])
            elif 4+self.DatiTrasformatori['Tipi di Trasformatori']['Normalizzati']+2 <= _icount < 4+self.DatiTrasformatori['Tipi di Trasformatori']['Normalizzati']+self.DatiTrasformatori['Tipi di Trasformatori']['Non normalizzati']+2:
                self.DatiTrasformatori['Dati per il calcolo dei costi del trasformatore'] = dict()
                self.DatiTrasformatori['Dati per il calcolo dei costi del trasformatore']['Pbase [MVA]'] = listValue[0]
                self.DatiTrasformatori['Dati per il calcolo dei costi del trasformatore']['Cbase [keuro]'] = listValue[1]
                self.DatiTrasformatori['Dati per il calcolo dei costi del trasformatore']['Vat_base [kV]'] = listValue[2]
                self.DatiTrasformatori['Dati per il calcolo dei costi del trasformatore']['Stallo_AT [keuro]'] = listValue[3]
                self.DatiTrasformatori['Dati per il calcolo dei costi del trasformatore']['Stallo_MT [keuro]'] = listValue[4]
        # Dati Curve Giornaliere di Default
        elif _idx == 17 or _idx == 18 or _idx == 19:
            if _icount == 0 and _idx == 17:
                self.DatiCurveGiornaliereDefault['Loads'] = dict()
                self.DatiCurveGiornaliereDefault['Gens'] = dict()
                self.DatiCurveGiornaliereDefault['EV'] = dict()
                self.DatiCurveGiornaliereDefault['Loads']['Dev. Stand. [p.u.]'] = list()
                self.DatiCurveGiornaliereDefault['Gens']['Dev. Stand. [p.u.]'] = list()
                self.DatiCurveGiornaliereDefault['EV']['Dev. Stand. [p.u.]'] = list()
            elif _icount == 2 and _idx == 17:
                self.DatiCurveGiornaliereDefault['Loads']['Residenziale'] = listValue[0:len(listValue)-1]
                self.DatiCurveGiornaliereDefault['Loads']['Dev. Stand. [p.u.]'].append(listValue[-1])
            elif _icount == 3 and _idx == 17:
                self.DatiCurveGiornaliereDefault['Loads']['Agricola'] = listValue[0:len(listValue)-1]
                self.DatiCurveGiornaliereDefault['Loads']['Dev. Stand. [p.u.]'].append(listValue[-1])
            elif _icount == 4 and _idx == 17:
                self.DatiCurveGiornaliereDefault['Loads']['Industriale'] = listValue[0:len(listValue) - 1]
                self.DatiCurveGiornaliereDefault['Loads']['Dev. Stand. [p.u.]'].append(listValue[-1])
            elif _icount == 5 and _idx == 17:
                self.DatiCurveGiornaliereDefault['Loads']['Ill. Pubblica'] = listValue[0:len(listValue) - 1]
                self.DatiCurveGiornaliereDefault['Loads']['Dev. Stand. [p.u.]'].append(listValue[-1])
            elif _icount == 6 and _idx == 17:
                self.DatiCurveGiornaliereDefault['Loads']['Terziario'] = listValue[0:len(listValue) - 1]
                self.DatiCurveGiornaliereDefault['Loads']['Dev. Stand. [p.u.]'].append(listValue[-1])
            elif _icount == 0 and _idx == 18:
                self.DatiCurveGiornaliereDefault['Gens']['Eolico'] = listValue[0:len(listValue) - 1]
                self.DatiCurveGiornaliereDefault['Gens']['Dev. Stand. [p.u.]'].append(listValue[-1])
            elif _icount == 1 and _idx == 18:
                self.DatiCurveGiornaliereDefault['Gens']['PV'] = listValue[0:len(listValue) - 1]
                self.DatiCurveGiornaliereDefault['Gens']['Dev. Stand. [p.u.]'].append(listValue[-1])
            elif _icount == 2 and _idx == 18:
                self.DatiCurveGiornaliereDefault['Gens']['FC'] = listValue[0:len(listValue) - 1]
                self.DatiCurveGiornaliereDefault['Gens']['Dev. Stand. [p.u.]'].append(listValue[-1])
            elif _icount == 3 and _idx == 18:
                self.DatiCurveGiornaliereDefault['Gens']['CHP'] = listValue[0:len(listValue) - 1]
                self.DatiCurveGiornaliereDefault['Gens']['Dev. Stand. [p.u.]'].append(listValue[-1])
            elif _icount == 4 and _idx == 18:
                self.DatiCurveGiornaliereDefault['Gens']['Turbogas'] = listValue[0:len(listValue) - 1]
                self.DatiCurveGiornaliereDefault['Gens']['Dev. Stand. [p.u.]'].append(listValue[-1])
            elif _icount == 0 and _idx == 19:
                self.DatiCurveGiornaliereDefault['EV']['Residenziale'] = listValue[0:len(listValue) - 1]
                self.DatiCurveGiornaliereDefault['EV']['Dev. Stand. [p.u.]'].append(listValue[-1])
        # Dati Rete di Distribuzione
        elif _idx == 20 or _idx == 21 or _idx == 22 or _idx == 23 or _idx == 24 or _idx == 25:
            if _icount == 0 and _idx == 20: #_idx == 19
                self.DatiReteDistribuzione['N cabine Primarie'] = dict()
                self.DatiReteDistribuzione['N cabine Primarie']['Esistenti'] = 0
                self.DatiReteDistribuzione['N cabine Primarie']['Future'] = 0

                self.DatiReteDistribuzione['N cabine Secondarie'] = dict()
                self.DatiReteDistribuzione['N cabine Secondarie']['Esistenti'] = 0
                self.DatiReteDistribuzione['N cabine Secondarie']['Future'] = 0

                self.DatiReteDistribuzione['Nodi CP'] = dict()
                self.DatiReteDistribuzione['Nodi CP']['N'] = list()
                self.DatiReteDistribuzione['Nodi CP']['Codice'] = list()
                self.DatiReteDistribuzione['Nodi CP']['Località'] = list()
                self.DatiReteDistribuzione['Nodi CP']['Tipo Interruttore'] = list()
                self.DatiReteDistribuzione['Nodi CP']['Tipologia'] = list()
                self.DatiReteDistribuzione['Nodi CP']['Coord X'] = list()
                self.DatiReteDistribuzione['Nodi CP']['Coord Y'] = list()
                self.DatiReteDistribuzione['Nodi CP']['Periodo Comparsa'] = list()
                self.DatiReteDistribuzione['Nodi CP']['SF6'] = list()
                self.DatiReteDistribuzione['Nodi CP']['N Trasf.'] = list()
                self.DatiReteDistribuzione['Nodi CP']['An'] = list()
                self.DatiReteDistribuzione['Nodi CP']['Tasso 1'] = list()

                self.DatiReteDistribuzione['Nodi MT'] = dict()
                self.DatiReteDistribuzione['Nodi MT']['N'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Codice'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Tipo Interruttore'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Tipologia'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Coord X'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Coord Y'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Periodo Comparsa'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Pc [kW]'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Cosfic'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Ag [kVA]'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Cosifg'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Utility'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Automatismo'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Tipo'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Dipendenza G'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Dipendenza C'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Premium'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Tipologia C'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Tipologia G'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Connessione'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Pmax DSM [%]'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Pmax GC [%]'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Tasso 1'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Pstorage [kW]'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Estorage [kWh]'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Emax [kWh]'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Emin [kWh]'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Initial SoC [%]'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Charging Station [kW]'] = list()
                self.DatiReteDistribuzione['Nodi MT']['Tipologia S'] = list()

                self.DatiReteDistribuzione['N Rami Esistenti'] = 0

                self.DatiReteDistribuzione['Rami'] = dict()
                self.DatiReteDistribuzione['Rami']['From'] = list()
                self.DatiReteDistribuzione['Rami']['To'] = list()
                self.DatiReteDistribuzione['Rami']['L Aerea [m]'] = list()
                self.DatiReteDistribuzione['Rami']['Indice Sezione Aerea'] = list()
                self.DatiReteDistribuzione['Rami']['L Cavo [m]'] = list()
                self.DatiReteDistribuzione['Rami']['Indice Sezione Cavo'] = list()
                self.DatiReteDistribuzione['Rami']['Flag Cavo-Aereo'] = list()
                self.DatiReteDistribuzione['Rami']['Stato Connessione'] = list()
            elif _icount == 1 and _idx == 20:
                self.DatiReteDistribuzione['Tensione Nominale [kV]'] = listValue[0]
            elif _icount == 3 and _idx == 20:
                self.DatiReteDistribuzione['N cabine Primarie']['Esistenti'] = listValue[0]
                self.DatiReteDistribuzione['N cabine Primarie']['Future'] = listValue[1]
            elif _icount == 4 and _idx == 20:
                self.DatiReteDistribuzione['N cabine Secondarie']['Esistenti'] = listValue[0]
                self.DatiReteDistribuzione['N cabine Secondarie']['Future'] = listValue[1]
            elif 1 <= _icount < 1+self.DatiReteDistribuzione['N cabine Primarie']['Esistenti'] and _idx == 21:
                self.DatiReteDistribuzione['Nodi CP']['N'].append(listValue['float'][0])
                self.DatiReteDistribuzione['Nodi CP']['Codice'].append(listValue['float'][1])
                self.DatiReteDistribuzione['Nodi CP']['Località'].append(listValue['string'][1])
                self.DatiReteDistribuzione['Nodi CP']['Tipo Interruttore'].append(listValue['float'][2])
                self.DatiReteDistribuzione['Nodi CP']['Tipologia'].append(listValue['float'][3])
                self.DatiReteDistribuzione['Nodi CP']['Coord X'].append(listValue['float'][4])
                self.DatiReteDistribuzione['Nodi CP']['Coord Y'].append(listValue['float'][5])
                self.DatiReteDistribuzione['Nodi CP']['Periodo Comparsa'].append(listValue['float'][6])
                self.DatiReteDistribuzione['Nodi CP']['SF6'].append(listValue['string'][2])
                self.DatiReteDistribuzione['Nodi CP']['N Trasf.'].append(listValue['float'][7])
            elif 1 <= _icount < 1+self.DatiReteDistribuzione['N cabine Primarie']['Esistenti'] and _idx == 22:
                self.DatiReteDistribuzione['Nodi CP']['An'].append(listValue['float'][2])
                self.DatiReteDistribuzione['Nodi CP']['Tasso 1'].append(listValue['float'][4])
            elif 1 <= _icount < 1 + self.DatiReteDistribuzione['N cabine Secondarie']['Esistenti'] and _idx == 23:
                self.DatiReteDistribuzione['Nodi MT']['N'].append(listValue['float'][0])
                self.DatiReteDistribuzione['Nodi MT']['Codice'].append(listValue['float'][1])
                self.DatiReteDistribuzione['Nodi MT']['Tipo Interruttore'].append(listValue['float'][2])
                self.DatiReteDistribuzione['Nodi MT']['Tipologia'].append(listValue['float'][3])
                self.DatiReteDistribuzione['Nodi MT']['Coord X'].append(listValue['float'][4])
                self.DatiReteDistribuzione['Nodi MT']['Coord Y'].append(listValue['float'][5])
                self.DatiReteDistribuzione['Nodi MT']['Periodo Comparsa'].append(listValue['float'][6])
                self.DatiReteDistribuzione['Nodi MT']['Pc [kW]'].append(listValue['float'][7])
                self.DatiReteDistribuzione['Nodi MT']['Cosfic'].append(listValue['float'][8])
                self.DatiReteDistribuzione['Nodi MT']['Ag [kVA]'].append(listValue['float'][9])
                self.DatiReteDistribuzione['Nodi MT']['Cosifg'].append(listValue['float'][10])
                self.DatiReteDistribuzione['Nodi MT']['Utility'].append(listValue['string'][1])
                self.DatiReteDistribuzione['Nodi MT']['Automatismo'].append(listValue['float'][11])
                self.DatiReteDistribuzione['Nodi MT']['Tipo'].append(listValue['string'][2])
                self.DatiReteDistribuzione['Nodi MT']['Dipendenza G'].append(listValue['float'][12])
                self.DatiReteDistribuzione['Nodi MT']['Dipendenza C'].append(listValue['float'][13])
                self.DatiReteDistribuzione['Nodi MT']['Premium'].append(listValue['float'][14])
                self.DatiReteDistribuzione['Nodi MT']['Tipologia C'].append(listValue['float'][15])
                self.DatiReteDistribuzione['Nodi MT']['Tipologia G'].append(listValue['float'][16])
                self.DatiReteDistribuzione['Nodi MT']['Connessione'].append(listValue['string'][3])
                self.DatiReteDistribuzione['Nodi MT']['Pmax DSM [%]'].append(listValue['float'][17])
                self.DatiReteDistribuzione['Nodi MT']['Pmax GC [%]'].append(listValue['float'][18])
                self.DatiReteDistribuzione['Nodi MT']['Tasso 1'].append(listValue['float'][19])
                self.DatiReteDistribuzione['Nodi MT']['Pstorage [kW]'].append(listValue['float'][20])
                self.DatiReteDistribuzione['Nodi MT']['Estorage [kWh]'].append(listValue['float'][21])
                self.DatiReteDistribuzione['Nodi MT']['Emax [kWh]'].append(listValue['float'][22])
                self.DatiReteDistribuzione['Nodi MT']['Emin [kWh]'].append(listValue['float'][23])
                self.DatiReteDistribuzione['Nodi MT']['Initial SoC [%]'].append(listValue['float'][24])
                self.DatiReteDistribuzione['Nodi MT']['Charging Station [kW]'].append(listValue['float'][25])
                self.DatiReteDistribuzione['Nodi MT']['Tipologia S'].append(listValue['float'][26])
            elif _icount == 0 and _idx == 24:
                self.DatiReteDistribuzione['N Rami Esistenti'] = listValue[0]
            elif 1 <= _icount < 1 + self.DatiReteDistribuzione['N Rami Esistenti'] and _idx == 25:
                self.DatiReteDistribuzione['Rami']['From'].append(listValue['float'][0])
                self.DatiReteDistribuzione['Rami']['To'].append(listValue['float'][1])
                self.DatiReteDistribuzione['Rami']['L Aerea [m]'].append(listValue['float'][2])
                self.DatiReteDistribuzione['Rami']['Indice Sezione Aerea'].append(listValue['float'][3])
                self.DatiReteDistribuzione['Rami']['L Cavo [m]'].append(listValue['float'][4])
                self.DatiReteDistribuzione['Rami']['Indice Sezione Cavo'].append(listValue['float'][5])
                self.DatiReteDistribuzione['Rami']['Flag Cavo-Aereo'].append(listValue['float'][6])
                self.DatiReteDistribuzione['Rami']['Stato Connessione'].append(listValue['string'][1])


if __name__ == "__main__":
    net = Net('LV_16nodi.dat')
    print(net.DatiReteDistribuzione['Nodi MT'])
    print(' ')
    print(net.DatiCurveGiornaliereDefault['EV']['Residenziale'])
    print(' ')
    # print(net.DatiReteDistribuzione['Nodi MT'])
    print(' ')
    # print(net.DatiReteDistribuzione['Rami'])
