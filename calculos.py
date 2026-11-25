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
ARQUIVO_PAINEL = RAIZ / "dados" / "painel" / "entulhos_painel.csv.gz"
ARQUIVO_META = RAIZ / "dados" / "painel" / "metadados.json"

CHAVE_ENDERECO = ["rua", "numero", "bairro"]
LIMIAR_PADRAO = 3
RPAS = [str(i) for i in range(1, 7)]
# A fonte 2025 termina em 10/09/2025; set–dez/2025 dependem quase só da fonte 2026.
INICIO_COBERTURA_LIMITADA = pd.Period("2025-09", freq="M")

NOMES_MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def rotulo_mes(p: pd.Period) -> str:
    return f"{NOMES_MESES[p.month - 1]}/{p.year}"


BOOLEANAS = ["no_recorte", "bairro_reconhecido", "endereco_ok", "sem_coordenadas", "mesmo_endereco_dia", "unico"]


def carregar_publicados() -> pd.DataFrame:
    """Todas as linhas publicadas do recorte 2024–2025, inclusive as repetidas (para a página de qualidade)."""
    df = pd.read_csv(ARQUIVO_PAINEL, dtype=str, keep_default_na=False)
    for col in BOOLEANAS:
        df[col] = df[col].map({"True": True, "False": False}).astype(bool)
    for col in ["abertura", "ultima_atualizacao"]:
        df[col] = pd.to_datetime(df[col], format="%Y-%m-%d", errors="coerce")
    for col in ["latitude", "longitude"]:
        df[col] = pd.to_numeric(df[col].replace("", None), errors="coerce")
    df = df.loc[df["no_recorte"]].copy()
    df["mes"] = df["abertura"].dt.to_period("M")
    return df.reset_index(drop=True)


def carregar_recorte() -> pd.DataFrame:
    """Chamados únicos com abertura em 2024 ou 2025 (recorte principal do projeto, sem repetições)."""
    df = carregar_publicados()
    return df.loc[df["unico"]].reset_index(drop=True)


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


def quadro_qualidade(df: pd.DataFrame, rep: dict | None = None) -> pd.DataFrame:
    """Problemas por campo. `df` = chamados únicos; `rep` = resumo de repetições das linhas publicadas."""
    n = len(df)
    itens = []
    if rep is not None:
        itens += [
            ("Repetição", "Mesmo chamado publicado em outro arquivo", rep["republicadas"],
             "Contado uma vez; fica a versão do arquivo mais recente."),
            ("Repetição", "Mais de um chamado no mesmo endereço e dia", rep["mesmo_dia"],
             "Contado como uma ocorrência; as linhas seguem marcadas na planilha."),
        ]
    itens += [
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
        ("Bairro", "Não reconhecido na lista de referência", int((~df["bairro_reconhecido"]).sum()),
         "Mantido como NÃO INFORMADO; RPA informada preservada."),
    ]
    q = pd.DataFrame(itens, columns=["Campo", "O que foi encontrado", "Chamados", "Decisão"])
    base = q["Chamados"].astype(float)
    if rep is not None:
        base.iloc[:2] = base.iloc[:2] / max(rep["publicadas"], 1) * 100
        base.iloc[2:] = base.iloc[2:] / max(n, 1) * 100
    else:
        base = base / max(n, 1) * 100
    q["%"] = base
    return q[["Campo", "O que foi encontrado", "Chamados", "%", "Decisão"]]


# ---------------------------------------------------------------- ajustes da revisão (entregável 7)
FAIXAS_DIAS = [(3, 3, "3 dias"), (4, 4, "4 dias"), (5, 5, "5 dias"), (6, 10, "6 a 10 dias"),
               (11, 20, "11 a 20 dias"), (21, 10_000, "21 dias ou mais")]


def faixas_recorrentes(candidatos: pd.DataFrame, limiar: int = LIMIAR_PADRAO) -> pd.DataFrame:
    """Endereços recorrentes por faixa de dias com chamado (só os que atingem o limiar)."""
    faixas = [(max(a, limiar), b, r) for a, b, r in FAIXAS_DIAS if b >= limiar]
    faixas = [(a, b, (f"{a} dias" if a == b else (f"{a} dias ou mais" if b >= 10_000 else f"{a} a {b} dias")))
              for a, b, _ in faixas]
    linhas = []
    for a, b, rotulo in faixas:
        m = candidatos["dias_distintos"].between(a, b)
        linhas.append({"faixa": rotulo, "enderecos": int(m.sum()), "chamados": int(candidatos.loc[m, "registros"].sum())})
    return pd.DataFrame(linhas)


def coerencia_enderecos(df: pd.DataFrame, enderecos: pd.DataFrame) -> pd.DataFrame:
    """Para cada endereço, a distância (m) das coordenadas dos chamados até o centro (mediana) do endereço.

    Serve para checar se a identificação textual aponta para um mesmo lugar. Só entram endereços com
    pelo menos 2 chamados com coordenadas dentro do retângulo aproximado do Recife.
    """
    colunas = CHAVE_ENDERECO + ["com_coordenadas", "distancia_mediana_m", "distancia_max_m"]
    if enderecos.empty:
        return pd.DataFrame(columns=colunas)
    e = df.loc[df["endereco_ok"]].merge(enderecos[CHAVE_ENDERECO], on=CHAVE_ENDERECO)
    e = e.loc[e["latitude"].between(-8.17, -7.92) & e["longitude"].between(-35.03, -34.84)]
    if e.empty:
        return pd.DataFrame(columns=colunas)
    centro = e.groupby(CHAVE_ENDERECO)[["latitude", "longitude"]].transform("median")
    import numpy as np
    dist = np.hypot((e["latitude"] - centro["latitude"]) * 111_000,
                    (e["longitude"] - centro["longitude"]) * 111_000 * np.cos(np.radians(8.05)))
    out = (e.assign(dist=dist).groupby(CHAVE_ENDERECO)
           .agg(com_coordenadas=("dist", "size"), distancia_mediana_m=("dist", "median"),
                distancia_max_m=("dist", "max")).reset_index())
    return out.loc[out["com_coordenadas"] >= 2].reset_index(drop=True)[colunas]


def bairros_da_rpa(df: pd.DataFrame, enderecos: pd.DataFrame, rpa: str) -> pd.DataFrame:
    """Bairros de uma RPA com o peso de cada um dentro da RPA."""
    b = por_bairro(df.loc[df["rpa"] == rpa], enderecos.loc[enderecos["rpa"] == rpa])
    total = b["registros"].sum()
    total_rec = b["enderecos_recorrentes"].sum()
    b["pct_rpa"] = 100 * b["registros"] / max(total, 1)
    b["pct_rpa_recorrentes"] = 100 * b["enderecos_recorrentes"] / max(total_rec, 1)
    return b


def bairro_lider_por_rpa(df: pd.DataFrame, enderecos: pd.DataFrame, campo: str = "registros") -> pd.DataFrame:
    linhas = []
    for rpa in RPAS:
        b = bairros_da_rpa(df, enderecos, rpa)
        b = b.loc[b["bairro"] != "NÃO INFORMADO"]
        if b.empty or b[campo].sum() == 0:
            continue
        pct = "pct_rpa" if campo == "registros" else "pct_rpa_recorrentes"
        topo = b.sort_values(campo, ascending=False).iloc[0]
        linhas.append({"rpa": rpa, "bairro": topo["bairro"], "valor": int(topo[campo]), "pct_rpa": topo[pct],
                       "total_rpa": int(b[campo].sum()), "bairros": int(len(b))})
    return pd.DataFrame(linhas)


def mes_por_ano(df: pd.DataFrame) -> pd.DataFrame:
    """Tabela com os meses nas linhas (jan–dez) e os anos nas colunas."""
    t = pd.crosstab(df["abertura"].dt.month, df["abertura"].dt.year).reindex(range(1, 13), fill_value=0)
    for ano in (2024, 2025):
        if ano not in t.columns:
            t[ano] = 0
    t = t[[2024, 2025]]
    t.index = [NOMES_MESES[m - 1] for m in t.index]
    t.index.name = "mes"
    return t


def repeticoes(publicados: pd.DataFrame) -> dict:
    """Resumo do tratamento de repetições para um recorte de linhas publicadas."""
    t = publicados["tipo_repeticao"]
    return {
        "publicadas": len(publicados),
        "republicadas": int(t.eq("Republicado em outro arquivo").sum()),
        "mesmo_dia": int(t.eq("Mesmo endereço e dia").sum()),
        "unicos": int(publicados["unico"].sum()),
        "grupos": int(publicados.loc[publicados["grupo_repeticao"].ne(""), "grupo_repeticao"].nunique()),
    }
