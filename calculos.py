"""Cálculos do painel, separados da interface para poderem ser testados.

Regras herdadas da EDA da Sprint 3 (notebook EDA_Central156_Sprint3):
  * unidade = linha publicada (não é protocolo único nem descarte confirmado);
  * endereço = rua padronizada + número padronizado + bairro de referência,
    somente quando "Endereço permite comparação?" = Sim;
  * recorrência = quantidade de DATAS de abertura distintas por endereço
    (vários chamados no mesmo dia contam como um dia);
  * limiar preliminar = 3 dias, consecutivos ou não (não é definição oficial da Emlurb).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent
ARQUIVO_PAINEL = RAIZ / "dados" / "painel" / "entulhos_painel.parquet"
ARQUIVO_META = RAIZ / "dados" / "painel" / "metadados.json"

CHAVE_ENDERECO = ["rua", "numero", "bairro"]
LIMIAR_PADRAO = 3
RPAS = [str(i) for i in range(1, 7)]
# A fonte 2025 termina em 10/09/2025; set–dez/2025 dependem quase só da fonte 2026.
INICIO_COBERTURA_LIMITADA = pd.Period("2025-09", freq="M")

NOMES_MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def rotulo_mes(p: pd.Period) -> str:
    return f"{NOMES_MESES[p.month - 1]}/{p.year}"


def carregar_recorte() -> pd.DataFrame:
    """Registros de entulhos com abertura em 2024 ou 2025 (recorte principal do projeto)."""
    df = pd.read_parquet(ARQUIVO_PAINEL)
    df = df.loc[df["no_recorte"].astype(bool)].copy()
    df["mes"] = df["abertura"].dt.to_period("M")
    for c in ["endereco_ok", "sem_coordenadas", "mesmo_endereco_dia"]:
        df[c] = df[c].astype(bool)
    return df.reset_index(drop=True)


def carregar_metadados() -> dict:
    return json.loads(ARQUIVO_META.read_text(encoding="utf-8"))


def filtrar(df: pd.DataFrame, mes_inicio: pd.Period, mes_fim: pd.Period,
            rpas: list[str] | None = None, bairros: list[str] | None = None,
            situacoes: list[str] | None = None, fontes: list[str] | None = None) -> pd.DataFrame:
    """Listas vazias ou None significam 'todos'."""
    m = df["mes"].between(mes_inicio, mes_fim)
    if rpas:
        m &= df["rpa"].isin(rpas)
    if bairros:
        m &= df["bairro"].isin(bairros)
    if situacoes:
        m &= df["situacao"].isin(situacoes)
    if fontes:
        m &= df["fonte"].isin(fontes)
    return df.loc[m]


def recorrencia(df: pd.DataFrame, limiar: int = LIMIAR_PADRAO) -> pd.DataFrame:
    """Uma linha por identificação de endereço, ordenada por dias distintos."""
    colunas = CHAVE_ENDERECO + ["rpa", "registros", "dias_distintos", "primeira_abertura",
                                "ultima_abertura", "quantidade_fontes", "candidato"]
    elegiveis = df.loc[df["endereco_ok"]]
    if elegiveis.empty:
        return pd.DataFrame(columns=colunas)
    end = (elegiveis.groupby(CHAVE_ENDERECO, sort=True)
           .agg(rpa=("rpa", "first"), registros=("abertura", "size"),
                dias_distintos=("abertura", "nunique"), primeira_abertura=("abertura", "min"),
                ultima_abertura=("abertura", "max"), quantidade_fontes=("fonte", "nunique"))
           .reset_index())
    end["candidato"] = end["dias_distintos"].ge(limiar)
    end = end.sort_values(["dias_distintos", "registros"] + CHAVE_ENDERECO,
                          ascending=[False, False, True, True, True]).reset_index(drop=True)
    return end[colunas]


def rotulo_endereco(linha: pd.Series) -> str:
    return f"{linha['rua']}, {linha['numero']} – {linha['bairro']}"


def distribuicao_dias(enderecos: pd.DataFrame, teto: int = 10) -> pd.DataFrame:
    """Quantidade de endereços por número de dias distintos (1, 2, …, teto, 'teto+1 ou mais')."""
    dias = enderecos["dias_distintos"].clip(upper=teto + 1)
    cont = dias.value_counts().reindex(range(1, teto + 2), fill_value=0)
    rotulos = [str(i) for i in range(1, teto + 1)] + [f"{teto + 1}+"]
    return pd.DataFrame({"dias": list(range(1, teto + 2)), "rotulo": rotulos, "enderecos": cont.values})


def serie_mensal(df: pd.DataFrame, mes_inicio: pd.Period, mes_fim: pd.Period) -> pd.DataFrame:
    meses = pd.period_range(mes_inicio, mes_fim, freq="M")
    tab = pd.crosstab(df["mes"], df["fonte"]).reindex(meses, fill_value=0)
    for f in ["Arquivo 2024", "Arquivo 2025", "Arquivo 2026"]:
        if f not in tab.columns:
            tab[f] = 0
    tab = tab[["Arquivo 2024", "Arquivo 2025", "Arquivo 2026"]]
    tab.index.name = "mes"
    tab["total"] = tab.sum(axis=1)
    return tab.reset_index()


def por_bairro(df: pd.DataFrame, enderecos: pd.DataFrame) -> pd.DataFrame:
    reg = df.groupby("bairro").agg(registros=("abertura", "size"), rpa=("rpa", "first"))
    cand = enderecos.loc[enderecos["candidato"]].groupby("bairro").size().rename("enderecos_recorrentes")
    out = reg.join(cand, how="left").fillna({"enderecos_recorrentes": 0})
    out["enderecos_recorrentes"] = out["enderecos_recorrentes"].astype(int)
    out["pct_registros"] = 100 * out["registros"] / max(len(df), 1)
    return out.reset_index().sort_values("registros", ascending=False, ignore_index=True)


def por_rpa(df: pd.DataFrame, enderecos: pd.DataFrame) -> pd.DataFrame:
    reg = df["rpa"].value_counts().reindex(RPAS, fill_value=0).rename("registros")
    cand = (enderecos.loc[enderecos["candidato"]]["rpa"].value_counts()
            .reindex(RPAS, fill_value=0).rename("enderecos_recorrentes"))
    out = pd.concat([reg, cand], axis=1).rename_axis("rpa").reset_index()
    out["pct_registros"] = 100 * out["registros"] / max(len(df), 1)
    return out


def coordenadas_por_fonte(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("fonte").agg(total=("sem_coordenadas", "size"), sem=("sem_coordenadas", "sum")).reset_index()
    g["com"] = g["total"] - g["sem"]
    g["pct_sem"] = 100 * g["sem"] / g["total"]
    g["pct_com"] = 100 - g["pct_sem"]
    return g


def quadro_qualidade(df: pd.DataFrame) -> pd.DataFrame:
    n = len(df)
    itens = [
        ("Coordenadas", "Sem latitude e longitude", int(df["sem_coordenadas"].sum()),
         "Mantido; posição não estimada."),
        ("Endereço", "Insuficiente para comparar endereços", int((~df["endereco_ok"]).sum()),
         "Fica fora da recorrência; entra nas contagens por mês, bairro e RPA."),
        ("Número", "Sem número identificável (SN, S/N)",
         int(df["conferencia_numero"].eq("Sem número identificável").sum()), "Não usado como local identificado."),
        ("Número", "Preenchido com zero", int(df["conferencia_numero"].eq("Preenchido com zero").sum()),
         "Zero não identifica o local."),
        ("Número", "Formato que precisa de revisão", int(df["conferencia_numero"].eq("Precisa de revisão").sum()),
         "Texto preservado; nenhum número escolhido."),
        ("Repetições", "Outro registro no mesmo endereço e dia", int(df["mesmo_endereco_dia"].sum()),
         "Sinalizado, não excluído; conta 1 dia na recorrência."),
        ("Bairro", "Não reconhecido na lista de referência", int((~df["bairro_reconhecido"]).sum()),
         "Mantido como NÃO INFORMADO; RPA informada preservada."),
    ]
    q = pd.DataFrame(itens, columns=["Campo", "O que foi encontrado", "Registros", "Decisão"])
    q["% do filtro"] = 100 * q["Registros"] / max(n, 1)
    return q[["Campo", "O que foi encontrado", "Registros", "% do filtro", "Decisão"]]
