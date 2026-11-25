"""Tratamento de registros repetidos (pedido na revisão do entregável 6).

Entrada : dados/entrada/dados_recife(4).xlsx  (planilha da Sprint 2, já com os três arquivos juntos)
Saída   : dados/entrada/dados_recife(5).xlsx  (mesma planilha + colunas e aba de repetições)

Por que é preciso
  O "Identificador na fonte" (_id do portal) é só a numeração da linha dentro de cada CSV: o mesmo
  número aparece nos três arquivos com chamados diferentes. Não há protocolo único. Por isso a
  repetição é identificada pelo conteúdo.

Regras (aplicadas depois de juntar os três arquivos)
  1. Republicação entre arquivos: mesma data de abertura + mesma rua, número e bairro INFORMADOS,
     em arquivos diferentes. É o mesmo chamado publicado de novo (ex.: aberto em 2024 e presente
     também no arquivo de 2025, com a situação atualizada). Conta uma vez.
  2. Mesmo endereço e mesmo dia: entre os registros com endereço identificável, mesma rua, número e
     bairro PADRONIZADOS na mesma data de abertura. Tratamos como uma única ocorrência naquele local
     e dia (chamados enviados mais de uma vez). Conta uma vez.
  Registros sem endereço identificável (SN, zero, número ambíguo) só são unidos pela regra 1:
  "RUA X, SN" no mesmo dia pode ser em pontos diferentes da rua.

Qual linha fica
  Em cada grupo fica a linha com coordenadas; empatando, a do arquivo mais recente (situação mais
  atual); depois a de última atualização mais recente. As outras ficam na planilha, marcadas, e saem
  das contagens do painel. Nada é apagado.

Uso:  python tratar_repeticoes.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

RAIZ = Path(__file__).resolve().parent
ENTRADA = RAIZ / "dados" / "entrada" / "dados_recife(4).xlsx"
SAIDA = RAIZ / "dados" / "entrada" / "dados_recife(5).xlsx"
ABA = "Entulhos tratados"
NOVAS = ["Grupo de repetição", "Tipo de repetição", "Conta como chamado único?", "Linha mantida no grupo"]

TIPO_REPUB = "Republicado em outro arquivo"
TIPO_DIA = "Mesmo endereço e dia"


def _norm(s: pd.Series) -> pd.Series:
    return s.astype("string").fillna("").str.upper().str.split().str.join(" ")


def ano(arquivo: str) -> int:
    achado = re.search(r"20\d{2}", str(arquivo))
    return int(achado.group()) if achado else 0


def marcar(base: pd.DataFrame) -> pd.DataFrame:
    """Devolve as quatro colunas novas, na ordem das linhas de `base`."""
    b = base.copy()
    b["_abertura"] = pd.to_datetime(b["Data de abertura"], errors="coerce").dt.normalize().astype(str)
    b["_ano_arq"] = b["Arquivo de origem"].map(ano)
    b["_ok"] = b["Endereço permite comparação?"].astype(str).str.strip().eq("Sim")
    b["_coord"] = (b["Latitude original"].astype(str).str.strip().ne("")
                   & b["Longitude original"].astype(str).str.strip().ne(""))
    b["_atual"] = pd.to_datetime(b["Última atualização"], errors="coerce")
    b["_rotulo"] = b["Arquivo de origem"].astype(str).map(lambda a: f"Arquivo {ano(a)}") + " · id " + \
        b["Identificador na fonte"].astype(str).str.strip()

    bruto = (b["_abertura"] + "|" + _norm(b["Rua informada"]) + "|" + _norm(b["Número informado"]) + "|"
             + _norm(b["Bairro informado"]))
    padronizado = (b["_abertura"] + "|" + _norm(b["Rua padronizada"]) + "|" + _norm(b["Número padronizado"])
                   + "|" + _norm(b["Bairro de referência"]))
    # Regra 1 para todos: dentro do mesmo arquivo, linhas iguais NÃO se juntam por esta regra
    # (a ordem dentro do arquivo separa); entre arquivos, a 1ª de cada arquivo se junta com a 1ª do outro.
    ordem = b.groupby([bruto, b["Arquivo de origem"]]).cumcount().astype(str)
    chave_r1 = "R|" + bruto + "|" + ordem
    # Regra 2 só para endereço identificável: a chave padronizada junta tudo no mesmo local e dia.
    chave = chave_r1.where(~b["_ok"], "E|" + padronizado)
    # Uma republicação de um registro com endereço identificável cai na mesma chave padronizada,
    # porque rua, número e bairro padronizados vêm dos informados.
    b["_chave"] = chave

    b = b.sort_values(["_chave", "_coord", "_ano_arq", "_atual"], ascending=[True, False, False, False])
    b["_n"] = b.groupby("_chave")["_chave"].transform("size")
    primeiro = ~b["_chave"].duplicated()
    mantida = b.loc[primeiro].set_index("_chave")
    b["_mantida_rotulo"] = b["_chave"].map(mantida["_rotulo"])
    b["_mantida_arq"] = b["_chave"].map(mantida["Arquivo de origem"])

    grupos = b.loc[b["_n"] > 1, "_chave"].drop_duplicates().reset_index(drop=True)
    numero = pd.Series(range(1, len(grupos) + 1), index=grupos.values)
    b["Grupo de repetição"] = b["_chave"].map(numero).map(lambda n: f"G{int(n):05d}" if pd.notna(n) else "")

    def tipo(linha) -> str:
        if linha["_n"] == 1:
            return ""
        if linha["_chave"].startswith("R|"):
            return TIPO_REPUB
        return TIPO_REPUB if linha["Arquivo de origem"] != linha["_mantida_arq"] else TIPO_DIA

    b["Tipo de repetição"] = b.apply(tipo, axis=1)
    b.loc[primeiro, "Tipo de repetição"] = b.loc[primeiro, "Tipo de repetição"].where(
        b.loc[primeiro, "_n"].eq(1), "Linha mantida")
    b["Conta como chamado único?"] = primeiro.map({True: "Sim", False: "Não"})
    b["Linha mantida no grupo"] = b["_mantida_rotulo"].where(b["_n"] > 1, "")
    return b.loc[base.index, NOVAS]


def resumo(base: pd.DataFrame, novas: pd.DataFrame) -> pd.DataFrame:
    recorte = base["Entra no período 2024–2025?"].astype(str).str.strip().eq("Sim")
    linhas = []
    for nome, m in [("Base de entulhos (todos os anos)", pd.Series(True, index=base.index)),
                    ("Recorte 2024–2025", recorte)]:
        t = novas.loc[m, "Tipo de repetição"]
        linhas.append({
            "Base": nome,
            "Linhas publicadas": int(m.sum()),
            "Republicadas em outro arquivo (saem)": int(t.eq(TIPO_REPUB).sum()),
            "Mesmo endereço e dia (saem)": int(t.eq(TIPO_DIA).sum()),
            "Chamados únicos (ficam)": int(novas.loc[m, "Conta como chamado único?"].eq("Sim").sum()),
            "Grupos de repetição": int(novas.loc[m & novas["Grupo de repetição"].ne(""),
                                                 "Grupo de repetição"].nunique()),
        })
    return pd.DataFrame(linhas)


def main() -> None:
    if not ENTRADA.is_file():
        sys.exit(f"Entrada não encontrada: {ENTRADA}")
    base = pd.read_excel(ENTRADA, sheet_name=ABA, dtype=object, keep_default_na=False)
    novas = marcar(base)
    tabela = resumo(base, novas)
    print(tabela.to_string(index=False))

    wb = load_workbook(ENTRADA)
    ws = wb[ABA]
    cabecalho = [c.value for c in ws[1]]
    if NOVAS[0] in cabecalho:
        sys.exit("A planilha de entrada já tem as colunas de repetição.")
    col0 = len(cabecalho) + 1
    destaque = PatternFill("solid", fgColor="F9EEDA")
    for j, nome in enumerate(NOVAS):
        cel = ws.cell(row=1, column=col0 + j, value=nome)
        cel.font = Font(bold=True)
        cel.fill = destaque
        cel.alignment = Alignment(wrap_text=True, vertical="top")
        ws.column_dimensions[cel.column_letter].width = 26
    valores = novas.to_numpy()
    for i in range(len(novas)):
        for j in range(len(NOVAS)):
            ws.cell(row=i + 2, column=col0 + j, value=valores[i, j] or None)

    if "Repetições" in wb.sheetnames:
        del wb["Repetições"]
    rs = wb.create_sheet("Repetições", index=wb.sheetnames.index(ABA) + 1)
    rs["A1"] = "Tratamento de registros repetidos"
    rs["A1"].font = Font(bold=True, size=13)
    textos = [
        "O Identificador na fonte é só a numeração da linha em cada CSV; não há protocolo único. "
        "A repetição foi identificada pelo conteúdo, depois de juntar os três arquivos.",
        "Regra 1 — Republicado em outro arquivo: mesma data de abertura e mesma rua, número e bairro "
        "informados, em arquivos diferentes. É o mesmo chamado publicado de novo.",
        "Regra 2 — Mesmo endereço e dia: com endereço identificável, mesma rua, número e bairro padronizados "
        "na mesma data. Conta como uma única ocorrência naquele local e dia.",
        "Sem endereço identificável (SN, zero, número ambíguo), só a regra 1 vale.",
        "Fica a linha com coordenadas; empatando, a do arquivo mais recente e a de atualização mais recente. "
        "As demais continuam na aba Entulhos tratados com 'Conta como chamado único?' = Não.",
    ]
    for i, t in enumerate(textos, start=3):
        rs.cell(row=i, column=1, value=t).alignment = Alignment(wrap_text=True, vertical="top")
        rs.merge_cells(start_row=i, start_column=1, end_row=i, end_column=6)
        rs.row_dimensions[i].height = 32
    inicio = 3 + len(textos) + 1
    for j, col in enumerate(tabela.columns, start=1):
        cel = rs.cell(row=inicio, column=j, value=col)
        cel.font = Font(bold=True)
        cel.fill = destaque
        cel.alignment = Alignment(wrap_text=True, vertical="top")
        rs.column_dimensions[cel.column_letter].width = 24
    for i, linha in enumerate(tabela.itertuples(index=False), start=inicio + 1):
        for j, v in enumerate(linha, start=1):
            rs.cell(row=i, column=j, value=v)
    rs.column_dimensions["A"].width = 34
    wb.save(SAIDA)
    print("Gerado:", SAIDA.relative_to(RAIZ))


if __name__ == "__main__":
    main()
