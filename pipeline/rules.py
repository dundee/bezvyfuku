# -*- coding: utf-8 -*-
"""
Pravidla vyberu a mapovani hodnot z RSV.

Prevzato z rsv_report.py. Mesicni XLSX report i data pro web pouzivaji
stejna pravidla, aby cisla na webu sedela s reportem.
"""

import re

# --------------------------------------------------------------------------
# Konfigurace vyberu
# --------------------------------------------------------------------------

# Populace reportu. Zahrnuje kategorie M1 i M1G, ale vylucuje vozidla
# se 'Druh vozidla = VOZIDLO ZVLASTNIHO URCENI' (sanitky, pohrebni vozy).
# Overeno proti reportu z dataovozidlech.cz: filtr na 'Kategorie vozidla = M1'
# dava o ~126 naftovych vozidel mesicne vic, nez web MD vykazuje.
DRUH_VOZIDLA = "OSOBNÍ AUTOMOBIL"

# Sloupce, ktere pipeline cte. Adresuji se jmenem z hlavicky, ne pozici.
COL_REG = "Datum 1. registrace"
COL_REG_CZ = "Datum 1. registrace v ČR"
COL_DRUH = "Druh vozidla"
COL_PALIVO = "Palivo"
COL_ZNACKA = "Tovární značka"

REQUIRED_COLUMNS = (COL_REG, COL_REG_CZ, COL_DRUH, COL_PALIVO, COL_ZNACKA)

# Pozor: sloupec 'Plne elektricke vozidlo' je v datech nespolehlivy
# (za srpen 2026 dava 1236 misto 1499), BEV se urcuje podle 'Palivo'.
PALIVO_BEV = "EL"


# --------------------------------------------------------------------------
# Mapovani hodnot
# --------------------------------------------------------------------------

# Kody paliv z registru -> nazvy pouzivane v reportu. Soupis vznikl z vsech
# hodnot, ktere se u osobnich vozidel objevily v letech 2024-2026.
# Neznamy kod se nezahazuje, projde pod svym syrovym jmenem a skript
# ho vypise jako upozorneni. Zamerne tu nejsou zjevne vadne zapisy
# ('BA + BA', 'NM + NM', '.', 'BA + .', 'BA 95 B+LPG+EL') - ty maji
# zustat viditelne, at je poznat, ze v registru neco nesedi.
PALIVO_LABELS = {
    "BA": "Benzin",
    "NM": "Nafta",
    "EL": "Elektropohon",
    "BA + EL": "Benzín + Elektropohon",
    "BA + LPG": "Benzín + LPG",
    "EL + BA": "Elektropohon + Benzín",
    "EL + NM": "Elektropohon + Nafta",
    "NM + EL": "Nafta + Elektropohon",
    "NM + BA": "Nafta + Benzín",
    "CNG": "CNG",
    "BA + CNG": "Benzín + CNG",
    "CNG+BA": "CNG + Benzín",
    "NM + CNG": "Nafta + CNG",
    "NG": "Zemní plyn",
    "BA + NG": "Benzín + zemní plyn",
    "LPG": "LPG",
    "NM + LPG": "Nafta + LPG",
    "PB+BA": "Propan-butan + Benzín",
    "BA + E 85": "Benzín + E85",
    "BA + E 95": "Benzín + E95",
    "E 85 + BA": "E85 + Benzín",
    "BA + E 85 + LPG": "Benzín + E85 + LPG",
    "BA + EL + LPG": "Benzín + Elektropohon + LPG",
    "EL + BA + LPG": "Elektropohon + Benzín + LPG",
    "BA SMĚS": "Benzín směs",
    "BA SMĚS + EL": "Benzín směs + Elektropohon",
    "BA SMĚS + LPG": "Benzín směs + LPG",
    "BA SMĚS + E 85 + LPG": "Benzín směs + E85 + LPG",
    "BA SMĚS + E 85 + CNG": "Benzín směs + E85 + CNG",
    "BIO NM": "Bionafta",
    "NM + BIO NM": "Nafta + Bionafta",
    "VODÍK": "Vodík",
}

# Sjednoceni ruznych zapisu tehoz vyrobce, aby mezirocni srovnani sedelo.
# Kazda polozka je vedomy soud, ne technicky fakt z dat:
#   VOLKSWAGEN / MERCEDES-BENZ  - zkracene nazvy z drivejsich reportu
#   KG MOBILITY, SSANGYONG      - stara a nova znacka teze automobilky
#   DFSK                        - Dongfeng Sokon, v datech jako model Seres 3
#   HYUNDAI, GENESIS            - rozbity zapis, jde o samostatnou znacku Genesis
ZNACKA_ALIASES = {
    "VOLKSWAGEN": "VW",
    "MERCEDES-BENZ": "MERCEDES",
    "KG MOBILITY": "SSANGYONG/KGM",
    "SSANGYONG": "SSANGYONG/KGM",
    "DFSK": "DONGFENG",
    "HYUNDAI, GENESIS": "GENESIS",
}


# --------------------------------------------------------------------------
# Skupiny paliv pro grafy na webu
# --------------------------------------------------------------------------

# Siroke skupiny pro grafy, poradi = poradi v legende. Na rozdil od
# PALIVO_LABELS (soupis kodu z let 2024-2026) musi pokryt i starsi zapisy
# ('BA ', 'BA 95 B', 'NM I NM BIO 48', ...), kterych je u novych aut
# v letech 2010-2015 kolem 30 %. Skupina se proto urcuje podle slozek kodu,
# ne podle celeho zapisu. Co se nezaradi ('.', 'VODÍK', preklepy), konci
# v 'Ostatní' - od roku 2010 je to pod 1 % rocne. BEV zustava presne
# PALIVO_BEV, stejne jako v reportu.
SKUPINA_BEV = "Elektro (BEV)"
PALIVO_SKUPINY = [SKUPINA_BEV, "Hybrid", "Benzín", "Nafta", "LPG", "CNG", "Ostatní"]

_PISMENO = r"[^\W\d_]"


def _slozka(pattern, kod):
    """Slozka kodu jako samostatne slovo: 'EL' v 'BA + EL', ne v 'DIESEL'."""
    return re.search(r"(?<!%s)(?:%s)(?!%s)" % (_PISMENO, pattern, _PISMENO), kod) is not None


def skupina_paliva(kod):
    if kod == PALIVO_BEV:
        return SKUPINA_BEV
    kod = kod.upper()
    elektro = _slozka("EL", kod)
    benzin = _slozka(r"BA|BENZ[IÍ]N|E ?85|E ?95", kod)
    nafta = _slozka("NM|NAFTA", kod)
    if elektro:
        return "Hybrid" if benzin or nafta else "Ostatní"
    if _slozka("LPG|PB", kod):
        return "LPG"
    if _slozka(r"CNG|LNG|NG|ZEMN[IÍ] PLYN", kod):
        return "CNG"
    if benzin:
        return "Benzín"
    if nafta:
        return "Nafta"
    return "Ostatní"
