"""Etapa de preparação do painel (dado tratado -> dado do painel).

Entrada : dados/entrada/dados_recife(5).xlsx  (planilha da Sprint 2 + tratamento de repetições,
          gerada por tratar_repeticoes.py a partir da dados_recife(4).xlsx)
Saída   : dados/painel/entulhos_painel.csv.gz

O script NÃO altera a entrada. Ele apenas:
  * lê a aba "Entulhos tratados" como texto (preserva SN, zeros e espaços);
  * converte datas, Sim/Não e coordenadas em cópias tipadas;
  * mantém somente as colunas que o painel usa, com nomes curtos;
  * leva as marcações de repetição (chamado único, tipo e grupo);
  * confere as contagens conhecidas da Sprint 2 e do tratamento de repetições e para se algo divergir.

Uso:  python tratar_repeticoes.py   (só quando a planilha (4) mudar)
      python preparar_dados.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import geo

RAIZ = Path(__file__).resolve().parent
ENTRADA = RAIZ / "dados" / "entrada" / "dados_recife(5).xlsx"
SAIDA = RAIZ / "dados" / "painel" / "entulhos_painel.csv.gz"
METADADOS = RAIZ / "dados" / "painel" / "metadados.json"

# Contagens publicadas no Plano de Preparação (Sprint 2). Servem de trava.
ESPERADO = {
    "linhas_base": 21_646,
    "linhas_recorte": 20_300,
    "endereco_suficiente": 17_134,
    "sem_coordenadas": 10_929,
    "mesmo_endereco_dia": 1_218,
    # Tratamento de repetições (tratar_repeticoes.py), no recorte 2024–2025:
    "chamados_unicos": 19_643,
    "republicados": 266,
    "mesmo_endereco_dia_removidos": 391,
    # Conferência das coordenadas com o mapa de bairros (preparar_mapa.py), entre os chamados únicos:
    "coord_no_bairro_informado": 7_956,
    "coord_em_outro_bairro": 893,
    "coord_fora_do_recife": 57,
}


def ler_sim_nao(serie: pd.Series, aceita_vazio: bool = False) -> pd.Series:
    s = serie.astype("string").str.strip().str.casefold()
    permitidos = {"sim", "não", "nao"} | ({""} if aceita_vazio else set())
    inesperado = sorted(set(s.dropna().unique()) - permitidos)
    if inesperado:
        raise ValueError(f"Preenchimento inesperado em Sim/Não: {inesperado}")
    return s.map({"sim": True, "não": False, "nao": False}).astype("boolean")


def ano_do_arquivo(nome: str) -> str:
    achado = re.search(r"20\d{2}", str(nome))
    return achado.group() if achado else str(nome)


def main() -> None:
    if not ENTRADA.is_file():
        sys.exit(f"Entrada não encontrada: {ENTRADA}")

    base = pd.read_excel(ENTRADA, sheet_name="Entulhos tratados", dtype=object, keep_default_na=False)
    texto = lambda c: base[c].astype("string").str.strip()  # noqa: E731

    abertura = pd.to_datetime(base["Data de abertura"], errors="coerce")
    atualizacao = pd.to_datetime(base["Última atualização"], errors="coerce")
    lat = pd.to_numeric(base["Latitude numérica"].replace("", pd.NA), errors="coerce")
    lon = pd.to_numeric(base["Longitude numérica"].replace("", pd.NA), errors="coerce")
    sem_coord = texto("Latitude original").eq("") | texto("Longitude original").eq("")

    painel = pd.DataFrame({
        "id_fonte": texto("Identificador na fonte"),
        "arquivo": texto("Arquivo de origem"),
        "fonte": base["Arquivo de origem"].map(ano_do_arquivo).map(lambda a: f"Arquivo {a}"),
        "abertura": abertura.dt.normalize(),
        "ultima_atualizacao": atualizacao.dt.normalize(),
        "no_recorte": ler_sim_nao(base["Entra no período 2024–2025?"]),
        "situacao": texto("Situação informada"),
        "rua_informada": texto("Rua informada"),
        "numero_informado": texto("Número informado"),
        "bairro_informado": texto("Bairro informado"),
        "rua": texto("Rua padronizada"),
        "numero": texto("Número padronizado"),
        "bairro": texto("Bairro de referência").replace("", "NÃO INFORMADO"),
        "bairro_reconhecido": texto("Bairro de referência").ne(""),
        # A RPA informada é usada para não perder os 7 registros sem bairro reconhecido.
        "rpa": texto("RPA informada"),
        "conferencia_numero": texto("Conferência do número"),
        "endereco_ok": ler_sim_nao(base["Endereço permite comparação?"]),
        "sem_coordenadas": sem_coord,
        "latitude": lat,
        "longitude": lon,
        "mesmo_endereco_dia": ler_sim_nao(base["Mesmo endereço e dia?"], aceita_vazio=True).fillna(False),
        "unico": ler_sim_nao(base["Conta como chamado único?"]),
        "tipo_repeticao": texto("Tipo de repetição"),
        "grupo_repeticao": texto("Grupo de repetição"),
    })

    # Conferência das coordenadas com o mapa oficial de bairros (dados/geo/bairros_recife.geojson).
    bairro_mapa = pd.Series(geo.localizar_bairro(painel["longitude"], painel["latitude"]), index=painel.index)
    painel["bairro_mapa"] = bairro_mapa
    painel["situacao_coord"] = np.select(
        [painel["latitude"].isna() | painel["longitude"].isna(), bairro_mapa.eq(""), bairro_mapa.eq(painel["bairro"])],
        ["Sem coordenadas", "Fora do Recife", "No bairro informado"], default="Em outro bairro")

    # Travas: se a entrada mudou, o painel não é gerado.
    recorte = painel.loc[painel["no_recorte"].astype(bool)]
    obtido = {
        "linhas_base": len(painel),
        "linhas_recorte": len(recorte),
        "endereco_suficiente": int(recorte["endereco_ok"].sum()),
        "sem_coordenadas": int(recorte["sem_coordenadas"].sum()),
        "mesmo_endereco_dia": int(recorte["mesmo_endereco_dia"].sum()),
        "chamados_unicos": int(recorte["unico"].sum()),
        "republicados": int(recorte["tipo_repeticao"].eq("Republicado em outro arquivo").sum()),
        "mesmo_endereco_dia_removidos": int(recorte["tipo_repeticao"].eq("Mesmo endereço e dia").sum()),
    }
    unicos = recorte.loc[recorte["unico"].astype(bool)]
    for chave, rotulo in [("coord_no_bairro_informado", "No bairro informado"),
                          ("coord_em_outro_bairro", "Em outro bairro"), ("coord_fora_do_recife", "Fora do Recife")]:
        obtido[chave] = int(unicos["situacao_coord"].eq(rotulo).sum())
    divergentes = {k: (obtido[k], v) for k, v in ESPERADO.items() if obtido[k] != v}
    if divergentes:
        sys.exit(f"Contagens diferentes da Sprint 2 (obtido, esperado): {divergentes}")
    assert painel["abertura"].notna().all(), "Há data de abertura inválida."
    assert recorte["abertura"].dt.year.isin([2024, 2025]).all()
    assert recorte["rpa"].isin(list("123456")).all()
    assert not painel.duplicated(["arquivo", "id_fonte"]).any()

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    # CSV compactado: lido só com pandas (sem pyarrow). Datas em ISO; Sim/Não como True/False.
    painel.to_csv(SAIDA, index=False, compression="gzip", date_format="%Y-%m-%d")

    fontes = pd.read_excel(ENTRADA, sheet_name="Fontes e períodos", dtype=object, keep_default_na=False)
    fontes = fontes.loc[fontes["Arquivo"].astype("string").str.strip().ne("")]
    meta = {
        "entrada": ENTRADA.name,
        "sha256_entrada": hashlib.sha256(ENTRADA.read_bytes()).hexdigest(),
        "contagens": obtido,
        "fontes": [
            {
                "arquivo": r["Arquivo"],
                "fonte": f"Arquivo {ano_do_arquivo(r['Arquivo'])}",
                "linhas_recebidas": int(r["Linhas recebidas"]),
                "entulhos": int(r["Registros de entulhos"]),
                "entulhos_2024_2025": int(r["Aberturas em 2024–2025"]),
                "primeira_abertura": pd.Timestamp(r["Primeira abertura de entulhos"]).strftime("%Y-%m-%d"),
                "ultima_abertura": pd.Timestamp(r["Última abertura de entulhos"]).strftime("%Y-%m-%d"),
            }
            for _, r in fontes.iterrows()
        ],
    }
    METADADOS.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Painel gerado:", SAIDA.relative_to(RAIZ), "|", len(painel), "linhas")
    print(json.dumps(obtido, ensure_ascii=False))


if __name__ == "__main__":
    main()
