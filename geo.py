"""Funções geográficas simples, só com numpy (sem shapely/geopandas).

* simplificar(): Douglas-Peucker em cada anel do polígono.
* localizar_bairro(): em qual bairro cai cada coordenada (ponto em polígono, regra par-ímpar).
* area_km2(): área aproximada de um polígono em km² (projeção equiretangular na latitude do Recife).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent
ARQUIVO_BAIRROS = RAIZ / "dados" / "geo" / "bairros_recife.geojson"
LAT_REF = -8.05  # latitude média do Recife
M_POR_GRAU = 111_320.0


def _poligonos(geometria: dict) -> list[list[list[list[float]]]]:
    """Lista de polígonos; cada polígono = lista de anéis (o 1º é o contorno, os outros são buracos)."""
    if geometria["type"] == "Polygon":
        return [geometria["coordinates"]]
    if geometria["type"] == "MultiPolygon":
        return geometria["coordinates"]
    raise ValueError(f"Geometria não suportada: {geometria['type']}")


def _dp(pontos: np.ndarray, tol: float) -> np.ndarray:
    if len(pontos) < 3:
        return pontos
    manter = np.zeros(len(pontos), dtype=bool)
    manter[[0, -1]] = True
    pilha = [(0, len(pontos) - 1)]
    while pilha:
        a, b = pilha.pop()
        if b <= a + 1:
            continue
        pa, pb = pontos[a], pontos[b]
        meio = pontos[a + 1:b]
        d = pb - pa
        comp = np.hypot(*d)
        if comp == 0:
            dist = np.hypot(*(meio - pa).T)
        else:
            dist = np.abs(d[1] * meio[:, 0] - d[0] * meio[:, 1] + pb[0] * pa[1] - pb[1] * pa[0]) / comp
        i = int(np.argmax(dist))
        if dist[i] > tol:
            k = a + 1 + i
            manter[k] = True
            pilha += [(a, k), (k, b)]
    return pontos[manter]


def simplificar_anel(anel: list[list[float]], tol: float) -> list[list[float]]:
    p = np.asarray(anel, dtype=float)[:, :2]
    if len(p) < 8:
        return np.round(p, 6).tolist()
    m = len(p) // 2  # anel fechado: divide em duas metades para o Douglas-Peucker funcionar
    s = np.vstack([_dp(p[: m + 1], tol), _dp(p[m:], tol)[1:]])
    if len(s) < 4:
        s = p
    return np.round(s, 6).tolist()


def area_km2(geometria: dict) -> float:
    total = 0.0
    kx = M_POR_GRAU * np.cos(np.radians(LAT_REF))
    for poli in _poligonos(geometria):
        for j, anel in enumerate(poli):
            p = np.asarray(anel, dtype=float)[:, :2]
            x, y = p[:, 0] * kx, p[:, 1] * M_POR_GRAU
            a = 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
            total += -a if j > 0 else a
    return total / 1e6


def _dentro_anel(x: np.ndarray, y: np.ndarray, anel: np.ndarray) -> np.ndarray:
    xs, ys = anel[:, 0], anel[:, 1]
    xs2, ys2 = np.roll(xs, -1), np.roll(ys, -1)
    dentro = np.zeros(len(x), dtype=bool)
    for x1, y1, x2, y2 in zip(xs, ys, xs2, ys2):
        cruza = (y1 > y) != (y2 > y)
        if not cruza.any():
            continue
        with np.errstate(divide="ignore", invalid="ignore"):
            xc = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
        dentro ^= cruza & (x < xc)
    return dentro


def dentro(geometria: dict, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    resultado = np.zeros(len(x), dtype=bool)
    for poli in _poligonos(geometria):
        contorno = np.asarray(poli[0], dtype=float)[:, :2]
        caixa = ((x >= contorno[:, 0].min()) & (x <= contorno[:, 0].max())
                 & (y >= contorno[:, 1].min()) & (y <= contorno[:, 1].max()))
        if not caixa.any():
            continue
        idx = np.flatnonzero(caixa)
        no_poli = _dentro_anel(x[idx], y[idx], contorno)
        for buraco in poli[1:]:
            no_poli &= ~_dentro_anel(x[idx], y[idx], np.asarray(buraco, dtype=float)[:, :2])
        resultado[idx[no_poli]] = True
    return resultado


def carregar_bairros(caminho: Path = ARQUIVO_BAIRROS) -> dict:
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def localizar_bairro(lon, lat, bairros: dict | None = None) -> np.ndarray:
    """Nome do bairro (propriedade `bairro`) em que cai cada ponto; "" quando fora do Recife ou sem coordenada."""
    bairros = bairros or carregar_bairros()
    x = np.asarray(lon, dtype=float)
    y = np.asarray(lat, dtype=float)
    ok = ~(np.isnan(x) | np.isnan(y))
    saida = np.full(len(x), "", dtype=object)
    for f in bairros["features"]:
        livre = ok & (saida == "")
        if not livre.any():
            break
        idx = np.flatnonzero(livre)
        achou = dentro(f["geometry"], x[idx], y[idx])
        saida[idx[achou]] = f["properties"]["bairro"]
    return saida
