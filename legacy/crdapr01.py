#*****************************************************************
#* PROGRAMA   : CRDAPR01                                          *
#* SISTEMA    : CARTERA - CREDITO DE CONSUMO                      *
#* FUNCION    : EVALUACION DE SOLICITUDES DE CREDITO              *
#* AREA       : DPTO. SISTEMAS                                    *
#* CREADO     : 1997-03-14                                        *
#*---------------------------------------------------------------*
#* MODIFICACIONES                                                 *
#* 1999-11-02  AJUSTE Y2K                                         *
#* 2003-06-20  CONVENIO COOPERATIVA                               *
#* 2006-09-05  SOL. 2210 - POLITICA DE SCORE                      *
#* 2008-02-11  SOL. 4471 - CAMPANA                                *
#* 2009-07-30  SOL. 5120 - LIBRANZA                               *
#* 2012-04-17  SOL. 7731 - MONTOS ALTOS                           *
#*---------------------------------------------------------------*
#* ENTRADA : WK-REG  PIC X(35)                                    *
#* SALIDA  : WK-RES  (VER TABLA AL FINAL)                         *
#*****************************************************************
#
# NOTA: este modulo es un sistema legacy SIMULADO para el experimento de GhostMind IA.
# Se escribio a proposito con estilo antiguo. GhostMind no lee este archivo.


def CRDAPR01(WK_REG):
    #-------------------------------------------------- VALIDA REG
    if WK_REG is None:
        return "ERR-REG"
    if len(WK_REG) != 35:
        return "ERR-LON"
    try:
        WS_A = int(WK_REG[0:3])
        WS_B = int(WK_REG[3:12])
        WS_C = int(WK_REG[12:21])
        WS_D = int(WK_REG[21:24])
        WS_E = int(WK_REG[24:27])
        WS_F = int(WK_REG[27:30])
    except ValueError:
        return "ERR-NUM"
    WS_G = WK_REG[30:31]
    WS_H = WK_REG[31:35]

    WS_RES = "  "
    WS_SW1 = 0
    WS_SW2 = 0

    #-------------------------------------------------- CALC CUOTA
    # CUOTA APROX (YA NO SE USA DESDE 2006)
    if WS_D > 0:
        WS_CUO = WS_C / WS_D
    else:
        WS_CUO = 0

    #-------------------------------------------------- EVALUACION
    if WS_H == "C-77":
        WS_RES = "AP"
    else:
        if WS_A < 21:
            WS_RES = "RC"
        else:
            if WS_G == "I":
                if WS_H == "C-45":
                    if WS_C >= 48000000:
                        if WS_C <= 50000000:
                            WS_SW2 = 1
            if WS_SW2 == 1:
                WS_RES = "RM"
            else:
                if WS_E < 400:
                    WS_RES = "RC"
                else:
                    if WS_G == "D":
                        if WS_F >= 120:
                            WS_RES = "RM"
                        else:
                            WS_RES = "RC"
                    else:
                        if WS_B < 1500000:
                            if WS_H != "C-12":
                                WS_SW1 = 1
                        if WS_SW1 == 1:
                            WS_RES = "RC"
                        else:
                            if WS_C > 80000000:
                                if WS_E >= 800 and WS_F >= 60:
                                    WS_RES = "AP"
                                else:
                                    WS_RES = "RM"
                            else:
                                if WS_E < 550:
                                    WS_RES = "RM"
                                else:
                                    WS_RES = "AP"

    #-------------------------------------------------- SALIDA
    # AP = APROBADO  RC = RECHAZADO  RM = REVISION MANUAL
    if WS_RES == "AP":
        return "APROBADO"
    if WS_RES == "RC":
        return "RECHAZADO"
    if WS_RES == "RM":
        return "REVISION_MANUAL"
    return "ERR-RES"
