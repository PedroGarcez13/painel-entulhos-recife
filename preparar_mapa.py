"""Gera o mapa de bairros usado no painel a partir do arquivo oficial da Prefeitura.

Fonte : Portal de Dados Abertos do Recife — conjunto "Área urbana", recurso "Bairros do Recife" (GeoJSON),
        https://dados.recife.pe.gov.br/dataset/area-urbana  · licença ODbL
Entrada: bairros-do-recife.geojson baixado do portal (2,2 MB, 94 bairros, coordenadas WGS84)
Saída  : dados/geo/bairros_recife.geojson (contornos simplificados com tolerância de ~5 m)

Uso:  python preparar_mapa.py caminho/para/bairros-do-recife.geojson
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geo

TOLERANCIA = 0.00005  # graus ≈ 5,5 m
FONTE = ("Portal de Dados Abertos do Recife — Área urbana / Bairros do Recife "
         "(https://dados.recife.pe.gov.br/dataset/area-urbana), licença ODbL")


def main(entrada: str) -> None:
    original = json.loads(Path(entrada).read_text(encoding="utf-8"))
    feicoes = []
    pontos_antes = pontos_depois = 0
    for f in original["features"]:
        p = f["properties"]
        g = f["geometry"]
        polis = geo._poligonos(g)
        novos = []
        for poli in polis:
            aneis = []
            for anel in poli:
                s = geo.simplificar_anel(anel, TOLERANCIA)
                pontos_antes += len(anel)
                pontos_depois += len(s)
                aneis.append(s)
            novos.append(aneis)
        geometria = ({"type": "Polygon", "coordinates": novos[0]} if len(novos) == 1
                     else {"type": "MultiPolygon", "coordinates": novos})
        feicoes.append({"type": "Feature", "properties": {
            "bairro": p["EBAIRRNOME"].strip().upper(),
            "nome": p["EBAIRRNOMEOF"].strip(),
            "rpa": str(int(p["CRPAAACODI"])),
            "codigo": int(p["CBAIRRCODI"]),
            "area_km2": round(geo.area_km2(g), 3),
        }, "geometry": geometria})
    feicoes.sort(key=lambda f: (f["properties"]["rpa"], f["properties"]["bairro"]))
    assert len(feicoes) == 94, len(feicoes)
    saida = {"type": "FeatureCollection", "fonte": FONTE, "tolerancia_graus": TOLERANCIA, "features": feicoes}
    geo.ARQUIVO_BAIRROS.parent.mkdir(parents=True, exist_ok=True)
    geo.ARQUIVO_BAIRROS.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    area = sum(f["properties"]["area_km2"] for f in feicoes)
    print(f"{len(feicoes)} bairros · {pontos_antes} → {pontos_depois} pontos · área total {area:.1f} km²")
    print("Gerado:", geo.ARQUIVO_BAIRROS.relative_to(geo.RAIZ), f"({geo.ARQUIVO_BAIRROS.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
