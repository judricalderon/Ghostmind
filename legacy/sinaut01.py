#*****************************************************************
#* PROGRAMA   : SINAUT01                                          *
#* SISTEMA    : SEGUROS GENERALES - AUTOMOVILES                   *
#* FUNCION    : LIQUIDACION DE RECLAMACIONES                      *
#* AREA       : DPTO. SISTEMAS                                    *
#* CREADO     : 1998-08-21                                        *
#*---------------------------------------------------------------*
#* MODIFICACIONES                                                 *
#* 1999-12-01  AJUSTE Y2K                                         *
#* 2002-03-15  SOL. 1187 - HURTO SOLO TODO RIESGO                 *
#* 2005-10-04  SOL. 3302 - CONTROL POLIZAS NUEVAS                 *
#* 2010-06-28  SOL. 6610 - PAGO RAPIDO                            *
#* 2014-01-09  SOL. 8045 - PERDIDAS TOTALES ALTAS                 *
#*---------------------------------------------------------------*
#* ENTRADA : WK-REG  PIC X(30)                                    *
#* SALIDA  : WK-RES  (VER TABLA AL FINAL)                         *
#*****************************************************************
#
# NOTA: este modulo es un sistema legacy SIMULADO para la demostracion de GhostMind IA
# (proyecto "seguros"). Se escribio a proposito con estilo antiguo. GhostMind no lee este archivo.


def SINAUT01(WK_REG):
    #-------------------------------------------------- VALIDA REG
    if WK_REG is None:
        return "ERR-REG"
    if len(WK_REG) != 30:
        return "ERR-LON"
    try:
        WS_A = int(WK_REG[0:4])
        WS_B = int(WK_REG[4:13])
        WS_C = int(WK_REG[13:22])
        WS_D = int(WK_REG[22:25])
        WS_E = int(WK_REG[25:26])
        WS_F = int(WK_REG[26:28])
    except ValueError:
        return "ERR-NUM"
    WS_G = WK_REG[28:29]
    WS_H = WK_REG[29:30]
    if WS_G not in ("C", "T", "H", "R"):
        return "ERR-COD"
    if WS_H not in ("B", "P"):
        return "ERR-COD"

    WS_RES = "  "
    WS_SW1 = 0

    #-------------------------------------------------- CALC DEDUCIBLE
    # DEDUCIBLE 10 % DEL ASEGURADO (SE LIQUIDA EN OTRO MODULO DESDE 2009)
    WS_DED = WS_C // 10
    if WS_DED > WS_B:
        WS_DED = WS_B

    #-------------------------------------------------- EVALUACION
    if WS_H == "P":
        if WS_B <= 5000000:
            WS_SW1 = 1
    if WS_SW1 == 1:
        WS_RES = "PG"
    else:
        if WS_H == "B" and WS_G == "H":
            WS_RES = "OB"
        else:
            if WS_D > 90:
                WS_RES = "OB"
            else:
                if WS_F < 18:
                    WS_RES = "OB"
                else:
                    if WS_A < 30:
                        WS_RES = "IN"
                    else:
                        if WS_E >= 6:
                            WS_RES = "IN"
                        else:
                            if WS_G == "T":
                                if WS_B > 80000000:
                                    WS_RES = "IN"
                                else:
                                    WS_RES = "PG"
                            else:
                                WS_RES = "PG"

    #-------------------------------------------------- SALIDA
    # PG = PAGAR  OB = OBJETAR  IN = INVESTIGAR
    if WS_RES == "PG":
        return "PAGAR"
    if WS_RES == "OB":
        return "OBJETAR"
    if WS_RES == "IN":
        return "INVESTIGAR"
    return "ERR-RES"
