"""Confere os números do painel sem filtros.

* Linhas publicadas: reproduzem a EDA da Sprint 3 (base antes do tratamento de repetições).
* Chamados únicos: base usada pelo painel depois do tratamento de repetições (revisão do entregável 6).

Rodar:  python -m pytest -q   (ou)   python tests/test_numeros_eda.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

import calculos as c  # noqa: E402

INICIO, FIM = pd.Period("2024-01", "M"), pd.Period("2025-12", "M")


def test_publicadas_reproduzem_eda():
    pub = c.carregar_publicados()
    assert len(pub) == 20_300
    assert int(pub["endereco_ok"].sum()) == 17_134
    end = c.recorrencia(pub, c.LIMIAR_PADRAO)
    cand = end.loc[end["candidato"]]
    assert len(end) == 11_556 and len(cand) == 931 and int(cand["registros"].sum()) == 4_646
    assert int(pub["mesmo_endereco_dia"].sum()) == 1_218
    mensal = c.serie_mensal(pub, INICIO, FIM).set_index("mes")["total"]
    assert mensal.max() == 1_669


def test_tratamento_de_repeticoes():
    pub = c.carregar_publicados()
    rep = c.repeticoes(pub)
    assert rep == {"publicadas": 20_300, "republicadas": 266, "mesmo_dia": 391, "unicos": 19_643, "grupos": 601}
    df = c.carregar_recorte()
    assert len(df) == 19_643
    # Com endereço identificável, sobra um chamado por endereço e dia.
    ok = df.loc[df["endereco_ok"]]
    assert not ok.duplicated(["abertura", "rua", "numero", "bairro"]).any()


def test_recorrencia_nao_muda_com_o_tratamento():
    df = c.carregar_recorte()
    end = c.recorrencia(df, c.LIMIAR_PADRAO)
    cand = end.loc[end["candidato"]]
    assert len(end) == 11_556 and len(cand) == 931
    assert int(end["dias_distintos"].eq(1).sum()) == 9_169
    assert (end["registros"] == end["dias_distintos"]).all()
    lider = end.iloc[0]
    assert (lider["rua"], lider["numero"], lider["bairro"], lider["dias_distintos"]) == (
        "RUA CORONEL OLIVEIRA", "53", "AFOGADOS", 71)
    fx = c.faixas_recorrentes(cand)
    assert fx["enderecos"].sum() == 931


def test_tempo_territorio_qualidade_unicos():
    df = c.carregar_recorte()
    end = c.recorrencia(df, c.LIMIAR_PADRAO)
    mensal = c.serie_mensal(df, INICIO, FIM).set_index("mes")["total"]
    assert mensal.sum() == 19_643
    assert mensal.idxmax() == pd.Period("2024-12", "M") and mensal.max() == 1_474
    tab = c.mes_por_ano(df)
    assert tab.to_numpy().sum() == 19_643 and tab.loc["dez", 2024] == 1_474
    r = c.por_rpa(df, end).set_index("rpa")["registros"].to_dict()
    assert r == {"1": 1_030, "2": 3_466, "3": 3_409, "4": 4_162, "5": 2_984, "6": 4_592}
    lid = c.bairro_lider_por_rpa(df, end).set_index("rpa")
    assert lid.loc["6", "bairro"] == "COHAB" and lid.loc["6", "valor"] == 1_192
    assert int(df["sem_coordenadas"].sum()) == 10_737


def test_coerencia_dos_enderecos():
    df = c.carregar_recorte()
    end = c.recorrencia(df, c.LIMIAR_PADRAO)
    coer = c.coerencia_enderecos(df, end.loc[end["candidato"]])
    assert len(coer) == 488
    assert round(100 * coer["distancia_mediana_m"].le(100).mean(), 1) == 97.5


def test_filtro_reduz_recorrencia():
    df = c.carregar_recorte()
    so_rpa6 = c.filtrar(df, INICIO, FIM, rpas=["6"])
    assert len(so_rpa6) == 4_592
    assert c.recorrencia(so_rpa6)["rpa"].eq("6").all()


if __name__ == "__main__":
    for nome, f in list(globals().items()):
        if nome.startswith("test_"):
            f()
            print("ok", nome)
