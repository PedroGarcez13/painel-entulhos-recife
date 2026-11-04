"""Confere se o painel, sem filtros, reproduz os números da EDA da Sprint 3.

Rodar:  python -m pytest -q   (ou)   python tests/test_numeros_eda.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

import calculos as c  # noqa: E402

INICIO, FIM = pd.Period("2024-01", "M"), pd.Period("2025-12", "M")


def _base():
    df = c.carregar_recorte()
    return df, c.recorrencia(df, c.LIMIAR_PADRAO)


def test_recorte_e_enderecos():
    df, end = _base()
    assert len(df) == 20_300
    assert int(df["endereco_ok"].sum()) == 17_134
    assert len(end) == 11_556
    assert int(end["registros"].sum()) == 17_134


def test_recorrencia():
    _, end = _base()
    cand = end.loc[end["candidato"]]
    assert len(cand) == 931
    assert int(cand["registros"].sum()) == 4_646
    assert int(end["dias_distintos"].eq(1).sum()) == 9_169
    lider = end.iloc[0]
    assert (lider["rua"], lider["numero"], lider["bairro"]) == ("RUA CORONEL OLIVEIRA", "53", "AFOGADOS")
    assert (lider["registros"], lider["dias_distintos"]) == (78, 71)


def test_tempo_territorio_qualidade():
    df, end = _base()
    mensal = c.serie_mensal(df, INICIO, FIM).set_index("mes")["total"]
    assert mensal.sum() == 20_300
    assert mensal.idxmax() == pd.Period("2024-12", "M") and mensal.max() == 1_669
    assert mensal.loc[pd.Period("2025-10", "M")] == 2
    b = c.por_bairro(df, end)
    assert (b.iloc[0]["bairro"], b.iloc[0]["registros"]) == ("COHAB", 1_217)
    r = c.por_rpa(df, end).set_index("rpa")["registros"].to_dict()
    assert r == {"1": 1_070, "2": 3_525, "3": 3_473, "4": 4_364, "5": 3_188, "6": 4_680}
    q = c.coordenadas_por_fonte(df).set_index("fonte")["sem"].to_dict()
    assert q == {"Arquivo 2024": 5_205, "Arquivo 2025": 5_582, "Arquivo 2026": 142}
    assert int(df["mesmo_endereco_dia"].sum()) == 1_218


def test_filtro_reduz_recorrencia():
    df, _ = _base()
    so_rpa6 = c.filtrar(df, INICIO, FIM, rpas=["6"])
    assert len(so_rpa6) == 4_680
    assert c.recorrencia(so_rpa6)["rpa"].eq("6").all()


if __name__ == "__main__":
    for nome, f in list(globals().items()):
        if nome.startswith("test_"):
            f()
            print("ok", nome)
