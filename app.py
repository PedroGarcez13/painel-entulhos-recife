"""Painel de recorrência de chamados de Remoção de Entulhos — Central 156 do Recife.

Entregável 4 (Dashboard Interativo — Versão Inicial) · Projeto 5 · CESAR School.
Executar:  streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import calculos as c

# ---------------------------------------------------------------- aparência
SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_MUDA = "#898781"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"
NEUTRO = "#c9c7bf"      # marcas fora de destaque
FAIXA = "#f0efec"       # sombreado de cobertura limitada
AZUL = "#2a78d6"        # série única
CORES_FONTE = {"Arquivo 2024": "#2a78d6", "Arquivo 2025": "#eb6834", "Arquivo 2026": "#1baf7a"}
CORES_COORD = {"Com coordenadas": "#2a78d6", "Sem coordenadas": "#eb6834"}
CONFIG_PLOTLY = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
                 "toImageButtonOptions": {"format": "png", "scale": 2}}

st.set_page_config(page_title="Entulhos no Recife · Central 156", page_icon="🗺️", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
  .block-container {padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1400px;}
  [data-testid="stMetricValue"] {font-size: 1.85rem;}
  [data-testid="stMetricLabel"] p {font-size: 0.86rem; color: #52514e; white-space: normal;}
  [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] div {overflow: visible !important;
      white-space: normal !important; text-overflow: clip !important;}
  .nota {color: #52514e; font-size: 0.9rem; line-height: 1.45;}
  .leitura {border-left: 3px solid #2a78d6; padding: 0.35rem 0 0.35rem 0.85rem; margin: 0.4rem 0 0.6rem 0;}
  .limite {color: #52514e; font-size: 0.86rem; border-left: 3px solid #c3c2b7;
           padding: 0.2rem 0 0.2rem 0.85rem; margin-bottom: 0.4rem;}
  .pergunta {font-size: 1.02rem; margin-bottom: 0.2rem;}
  h1 {font-size: 1.9rem !important; margin-bottom: 0.2rem !important;}
</style>
""", unsafe_allow_html=True)


def fmt_int(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def fmt_pct(x: float, casas: int = 1) -> str:
    return f"{x:.{casas}f}%".replace(".", ",")


def fmt_data(d) -> str:
    return pd.Timestamp(d).strftime("%d/%m/%Y")


def estilo(fig: go.Figure, altura: int, legenda: bool = False) -> go.Figure:
    fig.update_layout(
        height=altura, separators=",.", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", size=13, color=TINTA),
        margin=dict(l=8, r=40, t=48 if legenda else 16, b=8), showlegend=legenda,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text="", font=dict(color=TINTA_2)),
        hoverlabel=dict(bgcolor="white", bordercolor=EIXO, font=dict(color=TINTA, size=13)),
        bargap=0.28, barcornerradius=4,
    )
    eixos = dict(showgrid=False, linecolor=EIXO, tickfont=dict(color=TINTA_2), title_font=dict(color=TINTA_2),
                 zeroline=False, ticks="outside", ticklen=4, tickcolor="rgba(0,0,0,0)", automargin=True,
                 title_standoff=10)
    fig.update_xaxes(**eixos)
    fig.update_yaxes(**eixos)
    return fig


def grade_valores(fig: go.Figure, eixo: str, inteiros: bool = True) -> None:
    """Grade só no eixo de valores, em linha fina."""
    extra = {"tickformat": ",d"} if inteiros else {}
    (fig.update_yaxes if eixo == "y" else fig.update_xaxes)(showgrid=True, gridcolor=GRADE, gridwidth=1, **extra)


def mostrar(fig: go.Figure, chave: str) -> None:
    st.plotly_chart(fig, theme=None, config=CONFIG_PLOTLY, key=chave)


def leitura(texto: str) -> None:
    st.markdown(f'<div class="leitura">{texto}</div>', unsafe_allow_html=True)


def limite(texto: str) -> None:
    st.markdown(f'<div class="limite"><b>Limite:</b> {texto}</div>', unsafe_allow_html=True)


def baixar_csv(df: pd.DataFrame, nome: str, rotulo: str, chave: str) -> None:
    st.download_button(rotulo, df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                       file_name=nome, mime="text/csv", icon=":material/download:", key=chave)


# ---------------------------------------------------------------- dados
@st.cache_data(show_spinner="Carregando a base tratada…")
def dados() -> tuple[pd.DataFrame, dict]:
    return c.carregar_recorte(), c.carregar_metadados()


BASE, META = dados()
MESES = list(pd.period_range("2024-01", "2025-12", freq="M"))
SITUACOES = sorted(BASE["situacao"].unique())
FONTES = list(CORES_FONTE)
MESES_TXT = [str(m) for m in MESES]  # texto ("2024-01"): o select_slider guarda melhor valores simples
PADROES = {"f_rpa": [], "f_bairro": [], "f_situacao": [],
           "f_fonte": [], "f_limiar": c.LIMIAR_PADRAO}
for k, v in PADROES.items():
    st.session_state.setdefault(k, v)


st.session_state.setdefault("versao_periodo", 0)


def limpar_filtros() -> None:
    for k, v in PADROES.items():
        st.session_state[k] = v
    # O período usa uma chave nova a cada limpeza: o select_slider de intervalo
    # perde o par (início, fim) quando o valor é imposto pelo Session State.
    st.session_state["versao_periodo"] += 1


# ---------------------------------------------------------------- filtros (barra lateral)
with st.sidebar:
    st.markdown("### Filtros")
    st.caption("Todos os indicadores, gráficos e tabelas usam o mesmo recorte.")
    periodo = st.select_slider("Período de abertura", options=MESES_TXT, value=(MESES_TXT[0], MESES_TXT[-1]),
                               format_func=lambda t: c.rotulo_mes(pd.Period(t, freq="M")),
                               key=f"f_periodo_{st.session_state['versao_periodo']}")
    st.multiselect("RPA", c.RPAS, format_func=lambda r: f"RPA {r}", placeholder="Todas as RPAs", key="f_rpa")
    opcoes_bairro = sorted(BASE.loc[BASE["rpa"].isin(st.session_state["f_rpa"] or c.RPAS), "bairro"].unique())
    st.session_state["f_bairro"] = [b for b in st.session_state["f_bairro"] if b in opcoes_bairro]
    st.multiselect("Bairro", opcoes_bairro, placeholder="Todos os bairros", key="f_bairro",
                   help="A lista acompanha as RPAs escolhidas. Os 7 registros sem bairro reconhecido aparecem "
                        "como NÃO INFORMADO.")
    st.multiselect("Situação registrada", SITUACOES, placeholder="Todas as situações", key="f_situacao",
                   help="Fotografia da situação no arquivo publicado; não é o histórico do chamado.")
    st.multiselect("Arquivo de origem", FONTES, placeholder="Todos os arquivos", key="f_fonte",
                   help="Um chamado aberto em 2025 pode estar no arquivo de 2026. O ano do arquivo não é o ano "
                        "de abertura.")
    st.divider()
    st.slider("Recorrência: mínimo de dias distintos", 2, 10, key="f_limiar",
              help="Um endereço é candidato à recorrência quando tem chamados abertos em pelo menos este número "
                   "de datas diferentes, consecutivas ou não. O padrão do projeto é 3 (regra preliminar, não "
                   "oficial da Emlurb).")
    st.button("Limpar filtros", on_click=limpar_filtros, icon=":material/restart_alt:", width="stretch")

ini, fim = (pd.Period(t, freq="M") for t in periodo)
LIMIAR = st.session_state["f_limiar"]
DF = c.filtrar(BASE, ini, fim, st.session_state["f_rpa"], st.session_state["f_bairro"],
               st.session_state["f_situacao"], st.session_state["f_fonte"])
END = c.recorrencia(DF, LIMIAR)
CAND = END.loc[END["candidato"]]

# ---------------------------------------------------------------- cabeçalho
st.title("Remoção de entulhos no Recife: onde os chamados se repetem")
st.markdown(
    '<p class="nota">Chamados do serviço <b>Remoção de Entulhos</b> (código 6) da Central 156 da Emlurb, com '
    'abertura em <b>2024 e 2025</b>. Para quem acompanha a limpeza urbana: quais endereços voltam a aparecer, '
    'onde os registros se concentram e como variam no tempo. '
    '<b>Chamados registrados não confirmam descarte irregular nem pontos críticos oficiais.</b></p>',
    unsafe_allow_html=True)

filtros_ativos = []
if (ini, fim) != (MESES[0], MESES[-1]):
    filtros_ativos.append(f"{c.rotulo_mes(ini)} a {c.rotulo_mes(fim)}")
for chave, nome in [("f_rpa", "RPA"), ("f_bairro", "bairro"), ("f_situacao", "situação"), ("f_fonte", "arquivo")]:
    if st.session_state[chave]:
        valores = st.session_state[chave]
        filtros_ativos.append(f"{nome}: " + (", ".join(valores) if len(valores) <= 3 else f"{len(valores)} selecionados"))
st.caption(f"Mostrando **{fmt_int(len(DF))}** de {fmt_int(len(BASE))} registros do recorte"
           + (" · " + " · ".join(filtros_ativos) if filtros_ativos else " · sem filtros"))

if DF.empty:
    st.warning("Nenhum registro atende a esta combinação de filtros. Amplie o período ou remova algum filtro.")
    st.stop()

# ---------------------------------------------------------------- indicadores
mensal_total = c.serie_mensal(DF, ini, fim).set_index("mes")["total"]
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Registros", fmt_int(len(DF)), border=True,
          help="Linhas publicadas pela Central 156. Não são protocolos únicos confirmados.")
k2.metric(f"Endereços {LIMIAR}+ dias", fmt_int(len(CAND)), border=True,
          help=f"De {fmt_int(len(END))} endereços identificáveis "
               f"({fmt_pct(100 * len(CAND) / max(len(END), 1))}). Conta datas de abertura distintas.")
k3.metric("Registros neles", fmt_pct(100 * CAND["registros"].sum() / len(DF)), border=True,
          help=f"{fmt_int(CAND['registros'].sum())} das {fmt_int(len(DF))} linhas do recorte.")
k4.metric("Mês de pico", c.rotulo_mes(mensal_total.idxmax()), border=True,
          help=f"{fmt_int(mensal_total.max())} registros. A cobertura dos meses não foi comprovada como completa.")
k5.metric("Sem coordenadas", fmt_pct(100 * DF["sem_coordenadas"].mean()), border=True,
          help=f"{fmt_int(DF['sem_coordenadas'].sum())} registros sem latitude e longitude. Continuam em todas "
               f"as contagens; a posição não foi estimada.")

st.write("")
aba_rec, aba_ter, aba_tempo, aba_qual, aba_sobre = st.tabs(
    ["Recorrência", "Território", "Tempo", "Qualidade dos dados", "Sobre os dados"])

# ================================================================ 1. Recorrência
with aba_rec:
    st.markdown('<p class="pergunta"><b>Quais endereços voltam a aparecer em dias diferentes?</b></p>',
                unsafe_allow_html=True)
    st.markdown(f'<p class="nota">Endereço = rua e número padronizados + bairro de referência. Contamos as '
                f'<b>datas de abertura distintas</b>: vários chamados no mesmo dia contam como um dia. '
                f'Entram só os {fmt_int(DF["endereco_ok"].sum())} registros com endereço suficiente.</p>',
                unsafe_allow_html=True)

    if END.empty:
        st.info("Nenhum registro com endereço suficiente neste recorte.")
    else:
        col_a, col_b = st.columns([1, 1.25], gap="large")
        with col_a:
            st.markdown("**Quantos dias distintos cada endereço tem**")
            dist = c.distribuicao_dias(END)
            atinge = dist["dias"].ge(LIMIAR)
            fig = go.Figure()
            for flag, nome, cor in [(False, f"Menos de {LIMIAR} dias", NEUTRO), (True, f"{LIMIAR} dias ou mais", AZUL)]:
                parte = dist.loc[atinge.eq(flag)]
                fig.add_bar(x=parte["rotulo"], y=parte["enderecos"], name=nome, marker_color=cor,
                            text=[fmt_int(v) for v in parte["enderecos"]], textposition="outside",
                            textfont=dict(color=TINTA_2, size=12), cliponaxis=False, constraintext="none",
                            hovertemplate="%{x} dia(s): %{y:,} endereços<extra></extra>")
            fig.update_xaxes(type="category", categoryorder="array", categoryarray=dist["rotulo"],
                             title_text="Dias distintos de abertura", tickangle=0)
            fig.update_yaxes(title_text="Endereços", rangemode="tozero", tickformat=",d",
                             range=[0, dist["enderecos"].max() * 1.12])
            grade_valores(fig, "y")
            mostrar(estilo(fig, 380, legenda=True), "dist_dias")
            um_dia = int(END["dias_distintos"].eq(1).sum())
            leitura(f"<b>{fmt_pct(100 * um_dia / len(END))}</b> dos endereços têm registros em um único dia. "
                    f"<b>{fmt_int(len(CAND))}</b> ({fmt_pct(100 * len(CAND) / len(END), 2)}) chegam a {LIMIAR} dias "
                    f"ou mais e somam <b>{fmt_int(CAND['registros'].sum())}</b> registros, "
                    f"{fmt_pct(100 * CAND['registros'].sum() / len(DF), 2)} do recorte.")

        with col_b:
            topo_n = st.segmented_control("Mostrar", [10, 20, 30], default=10, format_func=lambda n: f"Top {n}",
                                          key="topo_n", label_visibility="collapsed") or 10
            st.markdown(f"**Os {topo_n} endereços com mais dias de registros**")
            topo = END.head(topo_n).iloc[::-1]
            rotulos = [c.rotulo_endereco(r) for _, r in topo.iterrows()]
            fig = go.Figure(go.Bar(
                y=rotulos, x=topo["dias_distintos"], orientation="h", marker_color=AZUL,
                text=topo["dias_distintos"], textposition="outside", textfont=dict(color=TINTA_2, size=12),
                cliponaxis=False,
                customdata=list(zip(topo["registros"], topo["primeira_abertura"].map(fmt_data),
                                    topo["ultima_abertura"].map(fmt_data), topo["rpa"], topo["quantidade_fontes"])),
                hovertemplate="<b>%{y}</b><br>%{x} dias distintos · %{customdata[0]} registros<br>"
                              "De %{customdata[1]} a %{customdata[2]} · RPA %{customdata[3]}<br>"
                              "Presente em %{customdata[4]} arquivo(s)<extra></extra>"))
            fig.update_xaxes(title_text="Dias distintos de abertura", rangemode="tozero")
            fig.update_yaxes(tickfont=dict(size=11.5, color=TINTA_2), automargin=True)
            grade_valores(fig, "x")
            mostrar(estilo(fig, max(380, 26 * len(topo) + 70)), "topo_end")
            lider = END.iloc[0]
            leitura(f"<b>{c.rotulo_endereco(lider)}</b>: {fmt_int(lider['registros'])} registros em "
                    f"{fmt_int(lider['dias_distintos'])} dias diferentes. Quantidade de registros e quantidade "
                    f"de dias são medidas diferentes.")

        limite("dias diferentes não comprovam descarte recorrente. A identificação é textual: pode ser um local de "
               "referência, e grafias diferentes do mesmo lugar podem continuar separadas. Nenhum endereço foi "
               "removido ou unido por suposição.")

        st.divider()
        st.markdown("**Histórico de um endereço**")
        st.markdown('<p class="nota">Clique em uma linha da tabela para ver as datas dos chamados daquele '
                    'endereço. A busca procura no nome da rua.</p>', unsafe_allow_html=True)
        busca_col, so_cand_col = st.columns([2, 1])
        busca = busca_col.text_input("Buscar rua", placeholder="Ex.: CORONEL OLIVEIRA", label_visibility="collapsed")
        so_candidatos = so_cand_col.toggle(f"Só endereços com {LIMIAR}+ dias", value=True)
        tabela = CAND if so_candidatos else END
        if busca.strip():
            tabela = tabela.loc[tabela["rua"].str.contains(busca.strip().upper(), regex=False, na=False)]
        tabela = tabela.reset_index(drop=True)
        tab_col, hist_col = st.columns([1.25, 1], gap="large")
        with tab_col:
            selecao = st.dataframe(
                tabela[["rua", "numero", "bairro", "dias_distintos", "registros"]],
                hide_index=True, height=380, on_select="rerun", selection_mode="single-row", key="tab_end",
                column_config={
                    "rua": st.column_config.TextColumn("Rua", width=165),
                    "numero": st.column_config.TextColumn("Nº", width=55),
                    "bairro": st.column_config.TextColumn("Bairro", width=120),
                    "dias_distintos": st.column_config.NumberColumn("Dias", format="%d", width=55),
                    "registros": st.column_config.NumberColumn("Registros", format="%d", width=78),
                })
            st.caption(f"{fmt_int(len(tabela))} endereços na tabela.")
        with hist_col:
            linhas_sel = selecao.selection.rows if selecao else []
            if tabela.empty:
                st.info("Nenhum endereço nesta seleção. Desligue o filtro de recorrência ou mude a busca.")
            else:
                escolhido = tabela.iloc[linhas_sel[0] if linhas_sel else 0]
                hist = DF.loc[(DF["rua"] == escolhido["rua"]) & (DF["numero"] == escolhido["numero"])
                              & (DF["bairro"] == escolhido["bairro"]) & DF["endereco_ok"]].sort_values("abertura")
                st.markdown(f"**{c.rotulo_endereco(escolhido)}**" + ("" if linhas_sel else " · selecione outro na tabela"))
                fig = go.Figure()
                for fonte, cor in CORES_FONTE.items():
                    parte = hist.loc[hist["fonte"] == fonte]
                    if parte.empty:
                        continue
                    fig.add_scatter(x=parte["abertura"], y=[fonte] * len(parte), mode="markers", name=fonte,
                                    marker=dict(size=10, color=cor, line=dict(color="white", width=2), opacity=0.9),
                                    customdata=list(zip(parte["abertura"].map(fmt_data), parte["situacao"])),
                                    hovertemplate="%{customdata[0]} · %{customdata[1]}<extra>%{y}</extra>")
                marcas = [m for m in pd.period_range(ini, fim, freq="M") if m.month in (1, 7)] or [ini]
                fig.update_xaxes(range=[ini.start_time - pd.Timedelta(days=10), fim.end_time + pd.Timedelta(days=10)],
                                 tickvals=[m.start_time for m in marcas], ticktext=[c.rotulo_mes(m) for m in marcas],
                                 title_text="Data de abertura")
                fig.update_yaxes(categoryorder="array", categoryarray=list(CORES_FONTE)[::-1])
                grade_valores(fig, "x", inteiros=False)
                mostrar(estilo(fig, 250, legenda=False), "hist_end")
                dias_rep = hist.groupby("abertura").size()
                st.markdown(
                    f'<p class="nota">{fmt_int(len(hist))} registros em {fmt_int(hist["abertura"].nunique())} dias · '
                    f'{fmt_int((dias_rep > 1).sum())} dia(s) com mais de um registro · situação mais recente '
                    f'informada: {hist.iloc[-1]["situacao"]}. Cada ponto é um registro; pontos no mesmo dia '
                    f'se sobrepõem.</p>', unsafe_allow_html=True)

        mesmo_dia = int(DF["mesmo_endereco_dia"].sum())
        st.caption(f"{fmt_int(mesmo_dia)} registros deste recorte compartilham endereço e dia com outro registro. "
                   f"Foram mantidos (não há protocolo global para confirmar duplicatas) e contam um único dia.")
        saida = END.assign(**{"Pelo menos o limiar?": END["candidato"].map({True: "Sim", False: "Não"}),
                              "Critério": f"Pelo menos {LIMIAR} dias distintos de abertura no recorte filtrado"})
        saida = saida.drop(columns="candidato").rename(columns={
            "rua": "Rua padronizada", "numero": "Número padronizado", "bairro": "Bairro de referência",
            "rpa": "RPA", "registros": "Registros", "dias_distintos": "Dias distintos",
            "primeira_abertura": "Primeira abertura", "ultima_abertura": "Última abertura",
            "quantidade_fontes": "Quantidade de arquivos"})
        baixar_csv(saida, "recorrencia_enderecos_filtrado.csv", "Baixar todos os endereços deste recorte (CSV)",
                   "dl_end")

# ================================================================ 2. Território
with aba_ter:
    st.markdown('<p class="pergunta"><b>Em quais bairros e regiões os registros se concentram?</b></p>',
                unsafe_allow_html=True)
    escolha = st.segmented_control("Medida", ["Registros", "Endereços recorrentes"], default="Registros",
                                   key="medida_ter", help=f"Endereços recorrentes = endereços com {LIMIAR} ou mais "
                                                          f"dias distintos de abertura (limiar da barra lateral).")
    escolha = escolha or "Registros"
    campo = "registros" if escolha == "Registros" else "enderecos_recorrentes"
    medida = "Registros" if campo == "registros" else f"Endereços com {LIMIAR}+ dias"
    bai = c.por_bairro(DF, END)
    rpa = c.por_rpa(DF, END)
    if st.session_state["f_rpa"]:
        rpa = rpa.loc[rpa["rpa"].isin(st.session_state["f_rpa"])]

    col_a, col_b = st.columns([1.35, 1], gap="large")
    with col_a:
        n_bai = 15
        top_bai = bai.loc[bai["bairro"] != "NÃO INFORMADO"].sort_values(campo, ascending=False).head(n_bai)
        st.markdown(f"**Os {min(n_bai, len(top_bai))} bairros com mais {medida.lower()}**")
        top_bai = top_bai.iloc[::-1]
        fig = go.Figure(go.Bar(
            y=top_bai["bairro"], x=top_bai[campo], orientation="h", marker_color=AZUL,
            text=[fmt_int(v) for v in top_bai[campo]], textposition="outside", cliponaxis=False,
            textfont=dict(color=TINTA_2, size=12),
            customdata=list(zip(top_bai["rpa"], top_bai["registros"], top_bai["enderecos_recorrentes"],
                                top_bai["pct_registros"].map(lambda v: fmt_pct(v, 2)))),
            hovertemplate="<b>%{y}</b> · RPA %{customdata[0]}<br>%{customdata[1]:,} registros "
                          "(%{customdata[3]} do recorte)<br>%{customdata[2]:,} endereços com "
                          f"{LIMIAR}+ dias<extra></extra>"))
        fig.update_xaxes(title_text=medida, rangemode="tozero")
        fig.update_yaxes(automargin=True)
        grade_valores(fig, "x")
        mostrar(estilo(fig, max(360, 27 * len(top_bai) + 70)), "bairros")
    with col_b:
        st.markdown(f"**{medida} por RPA**")
        fig = go.Figure(go.Bar(
            x=["RPA " + r for r in rpa["rpa"]], y=rpa[campo], marker_color=AZUL,
            text=[fmt_int(v) for v in rpa[campo]], textposition="outside", cliponaxis=False,
            textfont=dict(color=TINTA_2, size=12),
            customdata=list(zip(rpa["pct_registros"].map(lambda v: fmt_pct(v, 2)), rpa["registros"])),
            hovertemplate="<b>%{x}</b><br>%{customdata[1]:,} registros (%{customdata[0]} do recorte)"
                          "<extra></extra>"))
        fig.update_yaxes(title_text=medida, rangemode="tozero")
        grade_valores(fig, "y")
        mostrar(estilo(fig, 360), "rpas")

    bai_validos = bai.loc[bai["bairro"] != "NÃO INFORMADO"]
    if not bai_validos.empty:
        lb = bai_validos.sort_values(campo, ascending=False).iloc[0]
        lr = rpa.sort_values(campo, ascending=False).iloc[0]
        dez = bai_validos.sort_values("registros", ascending=False).head(10)["registros"].sum()
        leitura(f"<b>{lb['bairro']}</b> lidera em {medida.lower()} ({fmt_int(lb[campo])}). "
                f"Os dez bairros com mais registros somam <b>{fmt_pct(100 * dez / len(DF))}</b> do recorte. "
                f"Entre as regiões, a <b>RPA {lr['rpa']}</b> tem o maior valor "
                f"({fmt_int(lr[campo])}; {fmt_pct(lr['pct_registros'])} dos registros).")
    limite("são volumes absolutos, não taxas de risco. Bairros e RPAs têm população, área e uso do 156 diferentes, "
           "e esses denominadores ainda não entraram na análise. O código da RPA é uma categoria, não uma medida.")
    with st.expander("Ver tabela completa por bairro"):
        tb = bai.rename(columns={"bairro": "Bairro", "rpa": "RPA", "registros": "Registros",
                                 "enderecos_recorrentes": f"Endereços com {LIMIAR}+ dias",
                                 "pct_registros": "% do recorte"})
        st.dataframe(tb, hide_index=True, column_config={
            "% do recorte": st.column_config.NumberColumn(format="%.2f%%")})
        baixar_csv(tb, "registros_por_bairro.csv", "Baixar tabela (CSV)", "dl_bai")

# ================================================================ 3. Tempo
with aba_tempo:
    st.markdown('<p class="pergunta"><b>Como os registros variam ao longo dos meses?</b></p>',
                unsafe_allow_html=True)
    separar = st.toggle("Separar por arquivo de origem", value=True,
                        help="Mostra de qual CSV publicado veio cada registro. A fonte 2025 termina em 10/09/2025.")
    men = c.serie_mensal(DF, ini, fim)
    xs = list(range(len(men)))
    fig = go.Figure()
    if separar:
        for fonte, cor in CORES_FONTE.items():
            if men[fonte].sum() == 0:
                continue
            fig.add_bar(x=xs, y=men[fonte], name=fonte, marker_color=cor,
                        marker_line=dict(color=SUPERFICIE, width=1.5),
                        customdata=[c.rotulo_mes(m) for m in men["mes"]],
                        hovertemplate="%{customdata}: %{y:,} registros<extra>" + fonte + "</extra>")
        fig.update_layout(barmode="stack", legend_traceorder="normal")
    else:
        fig.add_bar(x=xs, y=men["total"], name="Registros", marker_color=AZUL,
                    customdata=[c.rotulo_mes(m) for m in men["mes"]],
                    hovertemplate="%{customdata}: %{y:,} registros<extra></extra>")
    meses_lim = [i for i, m in enumerate(men["mes"]) if m >= c.INICIO_COBERTURA_LIMITADA]
    if meses_lim:
        fig.add_vrect(x0=meses_lim[0] - 0.5, x1=meses_lim[-1] + 0.5, fillcolor=FAIXA, opacity=1, layer="below",
                      line_width=0)
        fig.add_annotation(x=(meses_lim[0] + meses_lim[-1]) / 2, y=1, yref="paper", yanchor="bottom",
                           text="Cobertura limitada", showarrow=False, font=dict(color=TINTA_2, size=12))
    viradas = [i for i, m in enumerate(men["mes"]) if m.month == 1 and i > 0]
    for i in viradas:
        fig.add_vline(x=i - 0.5, line_color=EIXO, line_width=1)
    passo = 1 if len(xs) <= 12 else 2
    fig.update_xaxes(tickmode="array", tickvals=xs[::passo], ticktext=[c.rotulo_mes(m) for m in men["mes"]][::passo],
                     title_text="Mês de abertura")
    fig.update_yaxes(title_text="Registros", rangemode="tozero")
    grade_valores(fig, "y")
    mostrar(estilo(fig, 420, legenda=separar), "mensal")

    mx, mn = men.loc[men["total"].idxmax()], men.loc[men["total"].idxmin()]
    texto = (f"O maior total observado é <b>{fmt_int(mx['total'])}</b> registros, em <b>{c.rotulo_mes(mx['mes'])}</b>; "
             f"o menor é {fmt_int(mn['total'])}, em {c.rotulo_mes(mn['mes'])}.")
    if meses_lim:
        texto += (" A queda a partir de set/2025 coincide com o fim da fonte 2025 (10/09/2025): esses meses "
                  "dependem quase só do arquivo de 2026 e não indicam queda real da demanda.")
    leitura(texto)
    limite("nenhum mês teve a completude comprovada. Por isso o painel não compara 2024 com 2025 como anos "
           "completos, nem afirma sazonalidade ou tendência.")
    with st.expander("Ver tabela mensal"):
        tm = men.assign(mes=[c.rotulo_mes(m) for m in men["mes"]]).rename(columns={"mes": "Mês", "total": "Total"})
        st.dataframe(tm, hide_index=True)
        baixar_csv(tm, "registros_por_mes.csv", "Baixar tabela (CSV)", "dl_mes")

# ================================================================ 4. Qualidade
with aba_qual:
    st.markdown('<p class="pergunta"><b>Quanto podemos confiar em cada campo deste recorte?</b></p>',
                unsafe_allow_html=True)
    col_a, col_b = st.columns([1.2, 1], gap="large")
    with col_a:
        st.markdown("**Registros com e sem coordenadas, por arquivo de origem**")
        cf = c.coordenadas_por_fonte(DF)
        rot_y = [f"{r['fonte']} · n={fmt_int(r['total'])}" for _, r in cf.iterrows()]
        fig = go.Figure()
        for nome, col_pct, col_n in [("Com coordenadas", "pct_com", "com"), ("Sem coordenadas", "pct_sem", "sem")]:
            fig.add_bar(y=rot_y, x=cf[col_pct], name=nome, orientation="h", marker_color=CORES_COORD[nome],
                        marker_line=dict(color=SUPERFICIE, width=2),
                        text=[fmt_pct(v) if v >= 12 else "" for v in cf[col_pct]], textposition="inside",
                        insidetextanchor="middle", textfont=dict(color="white", size=12),
                        customdata=cf[col_n],
                        hovertemplate="%{y}<br>" + nome + ": %{customdata:,} (%{x:.1f}%)<extra></extra>")
        fig.update_layout(barmode="stack", bargap=0.45, legend_traceorder="normal")
        fig.update_xaxes(range=[0, 100], ticksuffix="%", title_text="% dentro de cada arquivo")
        fig.update_yaxes(automargin=True, categoryorder="array", categoryarray=rot_y[::-1])
        grade_valores(fig, "x")
        mostrar(estilo(fig, 300, legenda=True), "coord")
    with col_b:
        st.write("")
        leitura(f"Faltam coordenadas em <b>{fmt_pct(100 * DF['sem_coordenadas'].mean())}</b> dos registros "
                f"filtrados. A ausência varia entre arquivos e também aparece em endereços completos, então "
                f"endereço incompleto não explica todos os casos.")
        limite("os arquivos não registram o motivo da falta. Usar só registros com coordenadas descartaria mais da "
               "metade da base e mudaria sua composição. Por isso esta versão <b>não tem mapa</b>: as coordenadas "
               "existentes ainda não passaram pela validação territorial dentro do Recife.")

    st.markdown("**Problemas encontrados e decisão tomada**")
    q = c.quadro_qualidade(DF)
    q["Registros"] = q["Registros"].map(fmt_int)
    st.dataframe(q, hide_index=True, column_config={
        "Campo": st.column_config.TextColumn(width=110),
        "O que foi encontrado": st.column_config.TextColumn(width=270),
        "Registros": st.column_config.TextColumn(width=90),
        "% do filtro": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100, width=140),
        "Decisão": st.column_config.TextColumn(width="large")})
    st.markdown('<p class="nota">Um mesmo registro pode ter mais de um problema. Nenhum valor ausente foi '
                'preenchido por estimativa: média de coordenadas inventaria posições, número escolhido inventaria '
                'endereços e data substituída mudaria o período.</p>', unsafe_allow_html=True)

# ================================================================ 5. Sobre
with aba_sobre:
    col_a, col_b = st.columns([1.2, 1], gap="large")
    with col_a:
        st.markdown("#### Fonte e recorte")
        st.markdown(
            "- **Fonte:** [Central de Atendimento de Serviços da Emlurb (156)]"
            "(https://dados.recife.pe.gov.br/dataset/central-de-atendimento-de-servicos-da-emlurb-156), "
            "Portal de Dados Abertos do Recife. Licença **ODbL**: atribuição obrigatória e compartilhamento pela "
            "mesma licença.\n"
            "- **Serviço:** grupo 2 (Limpeza Urbana), serviço 6 (Remoção de Entulhos).\n"
            "- **Período:** chamados com abertura em 2024 ou 2025, encontrados em qualquer um dos três arquivos.\n"
            "- **Base:** planilha tratada da Sprint 2 (`dados_recife(4)`, aba *Entulhos tratados*). Os CSVs "
            "originais não foram alterados.")
        fontes = pd.DataFrame(META["fontes"])[["fonte", "linhas_recebidas", "entulhos", "entulhos_2024_2025",
                                                "primeira_abertura", "ultima_abertura"]]
        fontes = fontes.rename(columns={"fonte": "Arquivo", "linhas_recebidas": "Linhas (todos os serviços)",
                                        "entulhos": "Entulhos (todos os anos)",
                                        "entulhos_2024_2025": "Entulhos 2024–2025",
                                        "primeira_abertura": "Primeira abertura", "ultima_abertura": "Última abertura"})
        for col in ["Linhas (todos os serviços)", "Entulhos (todos os anos)", "Entulhos 2024–2025"]:
            fontes[col] = fontes[col].map(fmt_int)
        for col in ["Primeira abertura", "Última abertura"]:
            fontes[col] = fontes[col].map(fmt_data)
        st.dataframe(fontes, hide_index=True)
        st.caption("As datas observadas em cada arquivo não comprovam que o período esteja completo.")

        st.markdown("#### Definições")
        st.markdown(
            "- **Registro:** uma linha publicada. Não é protocolo único nem descarte distinto.\n"
            "- **Endereço identificável:** rua, número com formato aceito e bairro reconhecido entre os 94 da "
            "referência oficial. SN, S/N, zero e números ambíguos ficam fora da comparação por endereço, mas "
            "continuam nas contagens por mês, bairro e RPA.\n"
            "- **Recorrência:** endereço com chamados abertos em pelo menos N datas diferentes (padrão 3), "
            "consecutivas ou não, dentro do recorte filtrado. Regra preliminar do projeto, não oficial da Emlurb.\n"
            "- **Situação e última atualização:** descrevem o cadastro; não comprovam a conclusão do serviço.")
    with col_b:
        st.markdown("#### O que este painel não afirma")
        st.markdown(
            "- Que um endereço recorrente seja ponto crítico oficial de descarte irregular.\n"
            "- Que um bairro tenha mais risco que outro (não há denominadores de população ou área).\n"
            "- Que a demanda caiu no fim de 2025 (efeito da cobertura dos arquivos).\n"
            "- Qualquer relação de causa, inclusive para a falta de coordenadas.")
        st.markdown("#### Diferença em relação à SR1")
        st.markdown(
            "A apresentação SR1 citava **1.288 endereços** com chamados em pelo menos 3 dias (27,8% dos chamados). "
            "O critério daquele cálculo não está documentado, e ele não pôde ser reproduzido sobre a base tratada da "
            "Sprint 2. Com a regra documentada (endereço identificável + datas de abertura distintas), o resultado "
            "sem filtros é **931 endereços**, que somam **22,89%** dos registros, igual à EDA da Sprint 3. "
            "O painel usa esse valor, recalculado a cada filtro.")
        st.markdown("#### Próximos passos")
        st.markdown(
            "- Validar as coordenadas dentro do território do Recife e só então incluir o mapa.\n"
            "- Revisar com a fonte os endereços extremos e as possíveis grafias duplicadas.\n"
            "- Testar o painel com usuários (entregável 7) e ajustar a leitura e os filtros.")
        st.caption(f"Entrada: {META['entrada']} · SHA-256 {META['sha256_entrada'][:16]}…")

st.divider()
st.caption("Fonte: Portal de Dados Abertos do Recife — Central de Atendimento de Serviços da Emlurb (156), licença ODbL. "
           "Tratamento e análise: equipe do Projeto 5 (Gestão Digital de Resíduos Sólidos Urbanos), CESAR School.")
