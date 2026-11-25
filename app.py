"""Painel de chamados de Remoção de Entulhos — Central 156 do Recife (2024–2025).

Projeto 5 · CESAR School. Versão revisada após o retorno do professor (entregável 7):
repetições tratadas, recorrência só entre endereços recorrentes, endereços conferidos com as
coordenadas, território por RPA e depois bairro, tempo em linhas por ano com tabela meses × anos.
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
  h1 {font-size: 1.75rem !important; margin-bottom: 0.2rem !important;}
  .marca {color: #52514e; font-size: 0.82rem; letter-spacing: 0.02em; text-transform: uppercase;
          margin-bottom: 0.1rem;}
  .achado-num {font-size: 1.6rem; font-weight: 600; line-height: 1.2; margin: 0.1rem 0 0.3rem 0;}
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


CORES_ANO = {2024: "#2a78d6", 2025: "#eb6834"}


# ---------------------------------------------------------------- dados
@st.cache_data(show_spinner="Carregando a base tratada…")
def dados() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    publicados = c.carregar_publicados()
    return publicados.loc[publicados["unico"]].reset_index(drop=True), publicados, c.carregar_metadados()


BASE, PUBLICADOS, META = dados()
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
    st.caption("Valem para todas as páginas.")
    periodo = st.select_slider("Período de abertura", options=MESES_TXT, value=(MESES_TXT[0], MESES_TXT[-1]),
                               format_func=lambda t: c.rotulo_mes(pd.Period(t, freq="M")),
                               key=f"f_periodo_{st.session_state['versao_periodo']}")
    st.multiselect("RPA (região)", c.RPAS, format_func=lambda r: f"RPA {r}", placeholder="Todas as RPAs",
                   key="f_rpa")
    opcoes_bairro = sorted(BASE.loc[BASE["rpa"].isin(st.session_state["f_rpa"] or c.RPAS), "bairro"].unique())
    st.session_state["f_bairro"] = [b for b in st.session_state["f_bairro"] if b in opcoes_bairro]
    st.multiselect("Bairro", opcoes_bairro, placeholder="Todos os bairros", key="f_bairro",
                   help="A lista mostra só os bairros das RPAs escolhidas. Chamados sem bairro reconhecido "
                        "aparecem como NÃO INFORMADO.")
    st.multiselect("Situação do chamado", SITUACOES, placeholder="Todas as situações", key="f_situacao",
                   help="Situação no arquivo publicado; não é o histórico do chamado.")
    st.multiselect("Arquivo de origem", FONTES, placeholder="Todos os arquivos", key="f_fonte",
                   help="Um chamado aberto em 2025 pode estar no arquivo de 2026. O ano do arquivo não é o ano "
                        "de abertura.")
    st.divider()
    st.slider("Endereço recorrente: mínimo de dias com chamado", 2, 10, key="f_limiar",
              help="Um endereço conta como recorrente quando recebeu chamados em pelo menos este número de "
                   "datas diferentes, consecutivas ou não. O padrão do projeto é 3 (regra preliminar, não "
                   "oficial da Emlurb).")
    st.button("Limpar filtros", on_click=limpar_filtros, icon=":material/restart_alt:", width="stretch")

ini, fim = (pd.Period(t, freq="M") for t in periodo)
LIMIAR = st.session_state["f_limiar"]
FILTROS = dict(rpas=st.session_state["f_rpa"], bairros=st.session_state["f_bairro"],
               situacoes=st.session_state["f_situacao"], fontes=st.session_state["f_fonte"])
DF = c.filtrar(BASE, ini, fim, **FILTROS)
PUB = c.filtrar(PUBLICADOS, ini, fim, **FILTROS)
END = c.recorrencia(DF, LIMIAR)
CAND = END.loc[END["candidato"]]


# ---------------------------------------------------------------- partes comuns a todas as páginas
def descricao_filtros() -> str:
    ativos = []
    if (ini, fim) != (MESES[0], MESES[-1]):
        ativos.append(f"{c.rotulo_mes(ini)} a {c.rotulo_mes(fim)}")
    for chave, nome in [("f_rpa", "RPA"), ("f_bairro", "bairro"), ("f_situacao", "situação"), ("f_fonte", "arquivo")]:
        if st.session_state[chave]:
            valores = st.session_state[chave]
            ativos.append(f"{nome}: " + (", ".join(valores) if len(valores) <= 3 else f"{len(valores)} selecionados"))
    if LIMIAR != c.LIMIAR_PADRAO:
        ativos.append(f"recorrente: {LIMIAR}+ dias")
    return " · ".join(ativos) if ativos else "sem filtros"


def indicadores() -> None:
    mensal_total = c.serie_mensal(DF, ini, fim).set_index("mes")["total"]
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Chamados", fmt_int(len(DF)), border=True,
              help="Chamados únicos de remoção de entulho, depois de tirar as repetições (mesmo chamado "
                   "em dois arquivos e mais de um chamado no mesmo endereço e dia).")
    k2.metric(f"Endereços recorrentes ({LIMIAR}+ dias)", fmt_int(len(CAND)), border=True,
              help=f"Endereços com chamados em {LIMIAR} ou mais datas diferentes, de {fmt_int(len(END))} "
                   f"endereços identificáveis ({fmt_pct(100 * len(CAND) / max(len(END), 1))}).")
    k3.metric("Chamados nesses endereços", fmt_pct(100 * CAND["registros"].sum() / len(DF)), border=True,
              help=f"{fmt_int(CAND['registros'].sum())} dos {fmt_int(len(DF))} chamados.")
    k4.metric("Mês com mais chamados", c.rotulo_mes(mensal_total.idxmax()), border=True,
              help=f"{fmt_int(mensal_total.max())} chamados. A cobertura dos meses não foi comprovada como completa.")
    k5.metric("Sem localização no mapa", fmt_pct(100 * DF["sem_coordenadas"].mean()), border=True,
              help=f"{fmt_int(DF['sem_coordenadas'].sum())} chamados sem latitude e longitude. Continuam em todas "
                   f"as contagens; a posição não foi estimada.")


def cabecalho(pergunta: str, nota: str | None = None) -> None:
    """Modelo comum: pergunta como título, nota, recorte ativo e indicadores."""
    st.markdown('<p class="marca">Remoção de entulhos · Central 156 do Recife · 2024–2025</p>',
                unsafe_allow_html=True)
    st.title(pergunta)
    if nota:
        st.markdown(f'<p class="nota">{nota}</p>', unsafe_allow_html=True)
    st.caption(f"Mostrando **{fmt_int(len(DF))}** de {fmt_int(len(BASE))} chamados · " + descricao_filtros())
    if DF.empty:
        st.warning("Nenhum chamado atende a esta combinação de filtros. Amplie o período ou remova algum filtro "
                   "na barra lateral (ou use Limpar filtros).")
        st.stop()
    indicadores()
    st.write("")


def subtitulo(texto: str) -> None:
    st.markdown(f"**{texto}**")


# ================================================================ 0. Visão geral
def pagina_visao_geral() -> None:
    cabecalho("Chamados de remoção de entulho no Recife",
              "Pedidos de <b>Remoção de Entulhos</b> (serviço 6) feitos à Central 156 da Emlurb, abertos em "
              "<b>2024 e 2025</b>. O painel mostra quais endereços pedem remoção várias vezes, onde os chamados se "
              "concentram e como variam mês a mês. <b>Um chamado não confirma descarte irregular nem ponto "
              "crítico oficial.</b>")
    subtitulo("Três achados deste recorte")
    mensal = c.serie_mensal(DF, ini, fim)
    pico = mensal.loc[mensal["total"].idxmax()]
    lider_rpa = c.por_rpa(DF, END).sort_values("registros", ascending=False).iloc[0]
    bai_rpa = c.bairros_da_rpa(DF, END, lider_rpa["rpa"])
    bai_rpa = bai_rpa.loc[bai_rpa["bairro"] != "NÃO INFORMADO"]

    c1, c2, c3 = st.columns(3, gap="medium")
    with c1, st.container(border=True, height="stretch"):
        subtitulo("Endereços que se repetem")
        if END.empty:
            st.markdown('<p class="nota">Nenhum chamado com endereço identificável neste recorte.</p>',
                        unsafe_allow_html=True)
        else:
            pct = 100 * CAND["registros"].sum() / len(DF)
            st.markdown(f'<p class="achado-num">{fmt_int(len(CAND))} endereços</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="nota">receberam chamados em {LIMIAR} dias ou mais e somam <b>{fmt_pct(pct)}</b> '
                        f'dos chamados. O que mais se repete é <b>{c.rotulo_endereco(END.iloc[0])}</b>, com '
                        f'{fmt_int(END.iloc[0]["dias_distintos"])} dias.</p>', unsafe_allow_html=True)
        st.page_link(PAG_REC, label="Ver endereços que se repetem", icon=":material/arrow_forward:")
    with c2, st.container(border=True, height="stretch"):
        subtitulo("RPAs e bairros")
        st.markdown(f'<p class="achado-num">RPA {lider_rpa["rpa"]}</p>', unsafe_allow_html=True)
        texto = f'tem mais chamados: <b>{fmt_int(lider_rpa["registros"])}</b> ({fmt_pct(lider_rpa["pct_registros"])}).'
        if not bai_rpa.empty:
            lb = bai_rpa.iloc[0]
            texto += f' Dentro dela, <b>{lb["bairro"]}</b> pesa mais ({fmt_pct(lb["pct_rpa"])} da RPA).'
        st.markdown(f'<p class="nota">{texto} São volumes, não taxas de risco.</p>', unsafe_allow_html=True)
        st.page_link(PAG_TER, label="Ver RPAs e bairros", icon=":material/arrow_forward:")
    with c3, st.container(border=True, height="stretch"):
        subtitulo("Chamados por mês")
        st.markdown(f'<p class="achado-num">{c.rotulo_mes(pico["mes"])}</p>', unsafe_allow_html=True)
        texto = f'é o mês com mais chamados (<b>{fmt_int(pico["total"])}</b>).'
        if fim >= c.INICIO_COBERTURA_LIMITADA:
            texto += " A queda depois de set/2025 vem do fim do arquivo de 2025, não de menos pedidos."
        st.markdown(f'<p class="nota">{texto}</p>', unsafe_allow_html=True)
        st.page_link(PAG_TEMPO, label="Ver chamados por mês", icon=":material/arrow_forward:")

    st.write("")
    rep = c.repeticoes(PUB)
    col_a, col_b = st.columns(2, gap="large")
    with col_a:
        subtitulo("Antes de usar estes números")
        st.markdown(
            f'<p class="nota">As {fmt_int(rep["publicadas"])} linhas publicadas viraram <b>{fmt_int(rep["unicos"])} '
            f'chamados</b> depois de tirar as repetições. Faltam coordenadas em '
            f'<b>{fmt_pct(100 * DF["sem_coordenadas"].mean())}</b> dos chamados, por isso o painel ainda não tem '
            f'mapa. Nenhum mês teve a cobertura comprovada como completa.</p>', unsafe_allow_html=True)
        st.page_link(PAG_QUAL, label="Ver a qualidade dos dados", icon=":material/arrow_forward:")
    with col_b:
        subtitulo("Como usar")
        st.markdown(
            '<p class="nota">Os filtros da barra lateral valem para todas as páginas e continuam ativos quando '
            'você troca de página. O último controle define quantos dias com chamado um endereço precisa ter '
            'para contar como recorrente (padrão 3).</p>', unsafe_allow_html=True)
        st.page_link(PAG_MET, label="Ver fonte, definições e decisões", icon=":material/arrow_forward:")


# ================================================================ 1. Endereços que se repetem
def pagina_recorrencia() -> None:
    cabecalho("Quais endereços pedem remoção de entulho várias vezes?",
              f'Endereço = rua e número padronizados + bairro. Contamos em quantos <b>dias diferentes</b> o '
              f'endereço recebeu chamado. Entram só os {fmt_int(DF["endereco_ok"].sum())} chamados com endereço '
              f'identificável (sem SN, zero ou número ambíguo).')
    if END.empty:
        st.info("Nenhum chamado com endereço identificável neste recorte.")
        return
    if CAND.empty:
        st.info(f"Nenhum endereço chegou a {LIMIAR} dias com chamado neste recorte. Diminua o mínimo de dias na "
                f"barra lateral ou amplie o período.")
        return

    col_a, col_b = st.columns([1, 1.25], gap="large")
    with col_a:
        subtitulo(f"Entre os {fmt_int(len(CAND))} endereços recorrentes, quantos dias com chamado cada um tem?")
        fx = c.faixas_recorrentes(CAND, LIMIAR)
        fig = go.Figure(go.Bar(
            y=fx["faixa"], x=fx["enderecos"], orientation="h",
            marker_color=[NEUTRO if i == 0 else AZUL for i in range(len(fx))],
            text=[f"{fmt_int(v)}  ({fmt_pct(100 * v / len(CAND))})" for v in fx["enderecos"]],
            textposition="outside", textfont=dict(color=TINTA_2, size=12), cliponaxis=False,
            customdata=fx["chamados"],
            hovertemplate="%{y}: %{x:,} endereços · %{customdata:,} chamados<extra></extra>"))
        fig.update_yaxes(categoryorder="array", categoryarray=fx["faixa"][::-1], title_text="")
        fig.update_xaxes(title_text="Endereços", rangemode="tozero", range=[0, fx["enderecos"].max() * 1.3])
        grade_valores(fig, "x")
        mostrar(estilo(fig, 330), "faixas_rec")
        poucos = int(fx["enderecos"].iloc[0])
        mais_10 = int(CAND["dias_distintos"].gt(10).sum())
        leitura(f"<b>{fmt_pct(100 * poucos / len(CAND))}</b> dos endereços recorrentes ficam no mínimo "
                f"({fx['faixa'].iloc[0]}). Só <b>{fmt_int(mais_10)}</b> passam de 10 dias: são os casos que mais se "
                f"repetem e os primeiros para revisar.")

    with col_b:
        subtitulo("Os 10 endereços com mais dias de chamado")
        topo = END.head(10).iloc[::-1]
        rotulos = [c.rotulo_endereco(r) for _, r in topo.iterrows()]
        fig = go.Figure(go.Bar(
            y=rotulos, x=topo["dias_distintos"], orientation="h", marker_color=AZUL,
            text=topo["dias_distintos"], textposition="outside", textfont=dict(color=TINTA_2, size=12),
            cliponaxis=False,
            customdata=list(zip(topo["primeira_abertura"].map(fmt_data), topo["ultima_abertura"].map(fmt_data),
                                topo["rpa"], topo["quantidade_fontes"])),
            hovertemplate="<b>%{y}</b><br>%{x} dias com chamado<br>"
                          "De %{customdata[0]} a %{customdata[1]} · RPA %{customdata[2]}<extra></extra>"))
        fig.update_xaxes(title_text="Dias com chamado", rangemode="tozero")
        fig.update_yaxes(tickfont=dict(size=11.5, color=TINTA_2), automargin=True)
        grade_valores(fig, "x")
        mostrar(estilo(fig, 330), "topo_end")
        lider = END.iloc[0]
        leitura(f"<b>{c.rotulo_endereco(lider)}</b> recebeu chamados em {fmt_int(lider['dias_distintos'])} dias "
                f"diferentes, entre {fmt_data(lider['primeira_abertura'])} e {fmt_data(lider['ultima_abertura'])}.")

    # ---- os endereços fazem sentido?
    st.divider()
    subtitulo("Os endereços fazem sentido? Conferência com as coordenadas")
    coer = c.coerencia_enderecos(DF, CAND)
    if coer.empty:
        st.markdown('<p class="nota">Nenhum endereço recorrente com pelo menos dois chamados com coordenadas neste '
                    'recorte.</p>', unsafe_allow_html=True)
    else:
        ate100 = coer["distancia_mediana_m"].le(100)
        k1, k2, k3 = st.columns(3)
        k1.metric("Endereços conferidos", fmt_int(len(coer)), border=True,
                  help="Endereços recorrentes com pelo menos 2 chamados com coordenadas dentro do Recife.")
        k2.metric("Coerentes (até 100 m)", fmt_pct(100 * ate100.mean()), border=True,
                  help="Metade ou mais dos chamados do endereço está a até 100 m do ponto central dele.")
        k3.metric("Para revisar", fmt_int((~ate100).sum()), border=True,
                  help="Endereços cujos chamados ficam espalhados: pode ser grafia igual para locais diferentes.")
        leitura(f"Comparamos as coordenadas dos chamados de cada endereço. Em <b>{fmt_pct(100 * ate100.mean())}</b> "
                f"dos {fmt_int(len(coer))} endereços conferidos, os chamados caem a até 100 m do ponto central: o "
                f"mesmo texto de endereço aponta para o mesmo lugar. Os outros "
                f"{fmt_int((~ate100).sum())} ficam na tabela abaixo para revisão.")
        revisar = coer.loc[~ate100].sort_values("distancia_mediana_m", ascending=False)
        if not revisar.empty:
            with st.expander(f"Ver os {fmt_int(len(revisar))} endereços para revisar"):
                st.dataframe(revisar, hide_index=True, column_config={
                    "rua": st.column_config.TextColumn("Rua"), "numero": st.column_config.TextColumn("Nº"),
                    "bairro": st.column_config.TextColumn("Bairro"),
                    "com_coordenadas": st.column_config.NumberColumn("Chamados com coordenadas", format="%d"),
                    "distancia_mediana_m": st.column_config.NumberColumn("Distância típica (m)", format="%.0f"),
                    "distancia_max_m": st.column_config.NumberColumn("Distância máxima (m)", format="%.0f")})
    limite("dias diferentes não comprovam descarte irregular recorrente. A conferência só vale para os chamados "
           "com coordenadas, e grafias diferentes do mesmo lugar podem continuar separadas.")

    # ---- histórico de um endereço
    st.divider()
    subtitulo("Histórico de um endereço")
    st.markdown('<p class="nota">Clique em uma linha da tabela para ver as datas dos chamados daquele endereço. '
                'A busca procura no nome da rua.</p>', unsafe_allow_html=True)
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
            tabela[["rua", "numero", "bairro", "rpa", "dias_distintos"]],
            hide_index=True, height=380, on_select="rerun", selection_mode="single-row", key="tab_end",
            column_config={
                "rua": st.column_config.TextColumn("Rua", width=170),
                "numero": st.column_config.TextColumn("Nº", width=55),
                "bairro": st.column_config.TextColumn("Bairro", width=130),
                "rpa": st.column_config.TextColumn("RPA", width=45),
                "dias_distintos": st.column_config.NumberColumn("Dias com chamado", format="%d", width=110),
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
            st.markdown(
                f'<p class="nota">{fmt_int(hist["abertura"].nunique())} dias com chamado · situação mais recente '
                f'informada: {hist.iloc[-1]["situacao"]}. Cada ponto é um dia com chamado; a cor mostra o '
                f'arquivo em que ele foi publicado.</p>', unsafe_allow_html=True)

    saida = END.assign(**{"Recorrente?": END["candidato"].map({True: "Sim", False: "Não"}),
                          "Critério": f"Pelo menos {LIMIAR} dias com chamado no recorte filtrado"})
    saida = saida.drop(columns=["candidato", "registros"]).rename(columns={
        "rua": "Rua padronizada", "numero": "Número padronizado", "bairro": "Bairro de referência",
        "rpa": "RPA", "dias_distintos": "Dias com chamado",
        "primeira_abertura": "Primeiro chamado", "ultima_abertura": "Último chamado",
        "quantidade_fontes": "Quantidade de arquivos"})
    baixar_csv(saida, "enderecos_recorrencia.csv", "Baixar todos os endereços deste recorte (CSV)", "dl_end")


# ================================================================ 2. RPAs e bairros
def pagina_territorio() -> None:
    cabecalho("Quais RPAs e bairros concentram os chamados?",
              "Primeiro as seis RPAs (regiões político-administrativas do Recife); depois, dentro da RPA escolhida, "
              "quais bairros pesam mais.")
    escolha = st.segmented_control("Medir por", ["Chamados", "Endereços recorrentes"], default="Chamados",
                                   key="medida_ter", help=f"Endereços recorrentes = endereços com chamados em "
                                                          f"{LIMIAR} ou mais dias (controle da barra lateral).")
    escolha = escolha or "Chamados"
    campo = "registros" if escolha == "Chamados" else "enderecos_recorrentes"
    medida = "chamados" if campo == "registros" else f"endereços recorrentes ({LIMIAR}+ dias)"
    rpa = c.por_rpa(DF, END)
    if st.session_state["f_rpa"]:
        rpa = rpa.loc[rpa["rpa"].isin(st.session_state["f_rpa"])]
    total = max(int(rpa[campo].sum()), 1)

    # ---- 1. RPAs
    subtitulo(f"1. Quantos {medida} há em cada RPA?")
    col_a, col_b = st.columns([1.35, 1], gap="large")
    lideres = c.bairro_lider_por_rpa(DF, END, campo)
    if st.session_state["f_rpa"] and not lideres.empty:
        lideres = lideres.loc[lideres["rpa"].isin(st.session_state["f_rpa"])]
    with col_a:
        maior = rpa[campo].max()
        fig = go.Figure(go.Bar(
            x=["RPA " + r for r in rpa["rpa"]], y=rpa[campo],
            marker_color=[AZUL if v == maior else NEUTRO for v in rpa[campo]],
            text=[f"{fmt_int(v)}<br>{fmt_pct(100 * v / total)}" for v in rpa[campo]], textposition="outside",
            cliponaxis=False, textfont=dict(color=TINTA_2, size=12),
            hovertemplate="<b>%{x}</b><br>%{y:,} " + medida + "<extra></extra>"))
        fig.update_yaxes(title_text=medida.capitalize(), rangemode="tozero", range=[0, maior * 1.25 if maior else 1])
        grade_valores(fig, "y")
        mostrar(estilo(fig, 340), "rpas")
    with col_b:
        st.markdown("**Bairro que mais pesa em cada RPA**")
        if lideres.empty:
            st.info("Sem bairros reconhecidos neste recorte.")
        else:
            tl = lideres.assign(rpa="RPA " + lideres["rpa"]).rename(columns={
                "rpa": "RPA", "bairro": "Bairro com mais", "valor": medida.capitalize(),
                "pct_rpa": "% da RPA", "bairros": "Bairros na RPA"})[
                ["RPA", "Bairro com mais", medida.capitalize(), "% da RPA", "Bairros na RPA"]]
            st.dataframe(tl, hide_index=True, column_config={
                "% da RPA": st.column_config.NumberColumn(format="%.1f%%")})
    lr = rpa.sort_values(campo, ascending=False).iloc[0]
    leitura(f"A <b>RPA {lr['rpa']}</b> tem mais {medida} ({fmt_int(lr[campo])}; "
            f"{fmt_pct(100 * lr[campo] / total)} do recorte). A RPA {rpa.sort_values(campo).iloc[0]['rpa']} tem o menor "
            f"valor ({fmt_int(rpa[campo].min())}).")

    # ---- 2. bairros dentro da RPA
    st.divider()
    opcoes = list(rpa.loc[rpa["registros"] > 0, "rpa"])
    padrao = lr["rpa"] if lr["rpa"] in opcoes else (opcoes[0] if opcoes else None)
    if padrao is None:
        return
    rpa_sel = st.segmented_control("RPA", opcoes, default=padrao, format_func=lambda r: f"RPA {r}",
                                   key="rpa_sel_ter") or padrao
    bai = c.bairros_da_rpa(DF, END, rpa_sel)
    bai = bai.loc[bai["bairro"] != "NÃO INFORMADO"].sort_values(campo, ascending=False)
    pct_col = "pct_rpa" if campo == "registros" else "pct_rpa_recorrentes"
    subtitulo(f"2. Dentro da RPA {rpa_sel}, quais bairros pesam mais?")
    if bai.empty or bai[campo].sum() == 0:
        st.info(f"Sem {medida} com bairro reconhecido na RPA {rpa_sel} neste recorte.")
    else:
        mostra = bai.head(15).iloc[::-1]
        topo_valor = mostra[campo].max()
        fig = go.Figure(go.Bar(
            y=mostra["bairro"], x=mostra[campo], orientation="h",
            marker_color=[AZUL if v == topo_valor else NEUTRO for v in mostra[campo]],
            text=[f"{fmt_int(v)}  ({fmt_pct(p)} da RPA)" for v, p in zip(mostra[campo], mostra[pct_col])],
            textposition="outside", cliponaxis=False, textfont=dict(color=TINTA_2, size=12),
            customdata=list(zip(mostra["registros"], mostra["enderecos_recorrentes"])),
            hovertemplate="<b>%{y}</b><br>%{customdata[0]:,} chamados · %{customdata[1]:,} endereços "
                          f"recorrentes<extra>RPA {rpa_sel}</extra>"))
        fig.update_xaxes(title_text=medida.capitalize(), rangemode="tozero", range=[0, topo_valor * 1.45])
        fig.update_yaxes(automargin=True)
        grade_valores(fig, "x")
        mostrar(estilo(fig, max(300, 27 * len(mostra) + 70)), "bairros_rpa")
        b1 = bai.iloc[0]
        tres = bai.head(3)[pct_col].sum()
        leitura(f"Na RPA {rpa_sel}, <b>{b1['bairro']}</b> pesa mais: {fmt_pct(b1[pct_col])} dos {medida} da RPA. "
                f"Os três primeiros bairros somam {fmt_pct(tres)} da RPA, entre {fmt_int(len(bai))} bairros.")
    limite("são volumes absolutos, não taxas de risco. Bairros e RPAs têm população, área e uso do 156 diferentes, "
           "e esses denominadores ainda não entraram na análise.")
    with st.expander("Ver tabela completa por bairro"):
        tb = c.por_bairro(DF, END).rename(columns={
            "bairro": "Bairro", "rpa": "RPA", "registros": "Chamados",
            "enderecos_recorrentes": f"Endereços recorrentes ({LIMIAR}+ dias)", "pct_registros": "% do recorte"})
        tb = tb.sort_values(["RPA", "Chamados"], ascending=[True, False])
        st.dataframe(tb, hide_index=True, column_config={
            "% do recorte": st.column_config.NumberColumn(format="%.2f%%")})
        baixar_csv(tb, "chamados_por_bairro.csv", "Baixar tabela (CSV)", "dl_bai")


# ================================================================ 3. Chamados por mês
def pagina_tempo() -> None:
    cabecalho("Quantos chamados há em cada mês?",
              "Uma linha por ano, com os meses de janeiro a dezembro, e a tabela com os mesmos números logo abaixo.")
    tab = c.mes_por_ano(DF)
    anos = [a for a in (2024, 2025) if ini.year <= a <= fim.year]
    meses_no_filtro = {a: [m for m in range(1, 13) if ini <= pd.Period(year=a, month=m, freq="M") <= fim]
                       for a in anos}
    subtitulo("Chamados por mês, um ano em cada linha")
    fig = go.Figure()
    for a in anos:
        ms = meses_no_filtro[a]
        xs = [c.NOMES_MESES[m - 1] for m in ms]
        ys = [int(tab.loc[c.NOMES_MESES[m - 1], a]) for m in ms]
        limitado = [pd.Period(year=a, month=m, freq="M") >= c.INICIO_COBERTURA_LIMITADA for m in ms]
        corte = limitado.index(True) if True in limitado else len(ms)
        fig.add_scatter(x=xs[:corte], y=ys[:corte], mode="lines+markers", name=str(a),
                        line=dict(color=CORES_ANO[a], width=2.5), marker=dict(size=7),
                        hovertemplate="%{x}/" + str(a) + ": %{y:,} chamados<extra></extra>")
        if corte < len(ms):
            ini_tr = max(corte - 1, 0)
            fig.add_scatter(x=xs[ini_tr:], y=ys[ini_tr:], mode="lines+markers", name=f"{a} (cobertura limitada)",
                            line=dict(color=CORES_ANO[a], width=2, dash="dot"),
                            marker=dict(size=7, symbol="circle-open"),
                            hovertemplate="%{x}/" + str(a) + ": %{y:,} chamados (cobertura limitada)<extra></extra>")
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=c.NOMES_MESES, title_text="Mês de abertura")
    fig.update_yaxes(title_text="Chamados", rangemode="tozero")
    grade_valores(fig, "y")
    mostrar(estilo(fig, 400, legenda=True), "mes_ano")

    mensal = c.serie_mensal(DF, ini, fim)
    mx, mn = mensal.loc[mensal["total"].idxmax()], mensal.loc[mensal["total"].idxmin()]
    texto = (f"O mês com mais chamados é <b>{c.rotulo_mes(mx['mes'])}</b> ({fmt_int(mx['total'])}); o com menos é "
             f"{c.rotulo_mes(mn['mes'])} ({fmt_int(mn['total'])}).")
    if fim >= c.INICIO_COBERTURA_LIMITADA:
        texto += (" O trecho pontilhado de 2025 (set–dez) depende quase só do arquivo de 2026, porque o de 2025 "
                  "termina em 10/09/2025: a queda ali não indica menos pedidos.")
    leitura(texto)

    subtitulo("Tabela: meses nas linhas, anos nas colunas")
    tt = tab.astype("Int64")
    for a in (2024, 2025):
        fora = [c.NOMES_MESES[m - 1] for m in range(1, 13) if not (ini <= pd.Period(year=a, month=m, freq="M") <= fim)]
        tt.loc[fora, a] = pd.NA
    tt = tt[[a for a in (2024, 2025) if a in anos]]
    tt.columns = [str(a) for a in tt.columns]
    tt.loc["Total"] = tt.sum(numeric_only=True)
    tt = tt.reset_index().rename(columns={"mes": "Mês"})
    st.dataframe(tt, hide_index=True, column_config={a: st.column_config.NumberColumn(a, format="%d")
                                                     for a in tt.columns if a != "Mês"})
    st.caption("Meses fora do período do filtro ficam em branco. Set–dez/2025 têm cobertura limitada.")
    baixar_csv(tt, "chamados_mes_ano.csv", "Baixar tabela (CSV)", "dl_mes_ano")
    limite("nenhum mês teve a completude comprovada. Por isso o painel não afirma que um ano teve mais pedidos que "
           "o outro, nem sazonalidade ou tendência.")


# ================================================================ 4. Qualidade
def pagina_qualidade() -> None:
    cabecalho("Os dados são confiáveis? Repetições e campos faltando")
    rep = c.repeticoes(PUB)

    subtitulo("1. Chamados repetidos: o que foi feito")
    st.markdown('<p class="nota">Juntamos os três arquivos publicados e procuramos repetições pelo conteúdo, porque '
                'o identificador da fonte é só a numeração da linha em cada arquivo (o mesmo número aparece nos três '
                'com chamados diferentes).</p>', unsafe_allow_html=True)
    col_a, col_b = st.columns([1.2, 1], gap="large")
    with col_a:
        etapas = ["Linhas publicadas", "Mesmo chamado em outro arquivo", "Mesmo endereço e dia", "Chamados únicos"]
        valores = [rep["publicadas"], -rep["republicadas"], -rep["mesmo_dia"], rep["unicos"]]
        fig = go.Figure(go.Waterfall(
            x=etapas, y=valores, measure=["absolute", "relative", "relative", "total"],
            text=[fmt_int(abs(v)) if i in (0, 3) else "−" + fmt_int(abs(v)) for i, v in enumerate(valores)],
            textposition="outside", cliponaxis=False,
            connector=dict(line=dict(color=EIXO, width=1)),
            increasing=dict(marker=dict(color=NEUTRO)), decreasing=dict(marker=dict(color="#eb6834")),
            totals=dict(marker=dict(color=AZUL)),
            hovertemplate="%{x}: %{text}<extra></extra>"))
        fig.update_yaxes(title_text="Linhas", rangemode="tozero", range=[0, rep["publicadas"] * 1.12])
        grade_valores(fig, "y")
        mostrar(estilo(fig, 340), "repeticoes")
    with col_b:
        st.markdown(
            f'<div class="nota"><p><b>Mesmo chamado em outro arquivo ({fmt_int(rep["republicadas"])}).</b> Mesma data '
            f'de abertura e mesma rua, número e bairro informados, em arquivos diferentes. Quase sempre um chamado de '
            f'2024 que aparece de novo no arquivo de 2025 com a situação atualizada. Fica a versão mais recente.</p>'
            f'<p><b>Mesmo endereço e dia ({fmt_int(rep["mesmo_dia"])}).</b> Mais de um chamado para a mesma rua, '
            f'número e bairro na mesma data. Conta como uma ocorrência naquele local e dia.</p>'
            f'<p>Chamados sem endereço identificável (SN, zero) só são unidos pela primeira regra: "RUA X, SN" no '
            f'mesmo dia pode ser em pontos diferentes da rua.</p></div>', unsafe_allow_html=True)
    leitura(f"As <b>{fmt_int(rep['publicadas'])}</b> linhas publicadas viram <b>{fmt_int(rep['unicos'])}</b> chamados "
            f"únicos ({fmt_pct(100 * (rep['publicadas'] - rep['unicos']) / max(rep['publicadas'], 1))} a menos). "
            f"Todo o painel usa os chamados únicos. A contagem de dias por endereço não muda, porque já contava "
            f"cada dia uma vez.")
    limite("sem protocolo único, a repetição é inferida pelo conteúdo. Dois pedidos diferentes no mesmo endereço e "
           "dia passam a contar como um. As linhas repetidas não foram apagadas: continuam marcadas na planilha "
           "dados_recife(5), aba Entulhos tratados.")

    st.divider()
    subtitulo("2. Coordenadas: quantos chamados têm localização")
    col_a, col_b = st.columns([1.2, 1], gap="large")
    with col_a:
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
        leitura(f"Faltam coordenadas em <b>{fmt_pct(100 * DF['sem_coordenadas'].mean())}</b> dos chamados. A falta "
                f"aparece nos três arquivos e também em endereços completos, então endereço incompleto não explica "
                f"todos os casos.")
        limite("os arquivos não registram o motivo da falta. Usar só chamados com coordenadas descartaria mais da "
               "metade da base. Por isso esta versão <b>não tem mapa</b>.")

    st.divider()
    subtitulo("3. Todos os problemas encontrados e a decisão tomada")
    q = c.quadro_qualidade(DF, rep)
    q["Chamados"] = q["Chamados"].map(fmt_int)
    st.dataframe(q, hide_index=True, column_config={
        "Campo": st.column_config.TextColumn(width=100),
        "O que foi encontrado": st.column_config.TextColumn(width=270),
        "Chamados": st.column_config.TextColumn(width=80),
        "%": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100, width=130),
        "Decisão": st.column_config.TextColumn(width="large")})
    st.markdown('<p class="nota">Nas repetições, o % é sobre as linhas publicadas; nos demais, sobre os chamados '
                'únicos. Um chamado pode ter mais de um problema. Nenhum valor ausente foi preenchido por '
                'estimativa.</p>', unsafe_allow_html=True)


# ================================================================ 5. Metodologia
HISTORICO_DECISOES = pd.DataFrame([
    ("Sprint 2 · Preparação", "Recorte no serviço 6 (Remoção de Entulhos) e aberturas em 2024–2025.",
     "O grupo 2 mistura serviços diferentes; o ano do arquivo não é o ano de abertura."),
    ("Sprint 2 · Preparação", "Ausências mantidas: nenhuma coordenada, número ou data estimada.",
     "Estimar inventaria posições e endereços."),
    ("Sprint 2 · Preparação", "Mesmo endereço e dia sinalizado, não excluído.",
     "Não há protocolo global para confirmar duplicatas."),
    ("Sprint 3 · EDA", "Recorrência = datas de abertura distintas por endereço; limiar preliminar de 3 dias.",
     "Vários chamados no mesmo dia não inflam a recorrência."),
    ("Sprint 3 · EDA", "Nenhum extremo removido pela regra do IQR.",
     "Com Q1 = Q3 = 1, a regra marcaria todo endereço com mais de um dia."),
    ("Entregável 4 · Dashboard v1", "Streamlit, filtros globais e painel sem mapa.",
     "53,8% sem coordenadas e coordenadas ainda não validadas no território."),
    ("Entregável 5 · Proposta", "Seis páginas com o mesmo modelo e uma Visão geral na entrada.",
     "Quem acompanha a limpeza urbana precisa do resumo antes do detalhe."),
    ("Entregável 6 · Consolidado", "Navegação por páginas implementada; mapa continua adiado.",
     "A validação territorial das coordenadas ainda não foi feita."),
    ("Revisão do professor", "Três arquivos juntos e repetições tratadas: 20.300 linhas viram 19.643 chamados únicos.",
     "O mesmo chamado aparecia em dois arquivos, e havia vários chamados no mesmo endereço e dia."),
    ("Revisão do professor", "Recorrência mostrada só entre os endereços com 3+ dias; ranking fixo nos 10 primeiros.",
     "O histograma era dominado pelos endereços com um único dia e escondia o problema."),
    ("Revisão do professor", "Endereços conferidos com as coordenadas dos chamados.",
     "Confirmar se o mesmo texto de endereço aponta para o mesmo lugar."),
    ("Revisão do professor", "Território primeiro por RPA, depois bairros dentro da RPA.",
     "Responder qual bairro pesa mais em cada região."),
    ("Revisão do professor", "Tempo em linhas (um ano por linha) e tabela meses × anos.",
     "Comparar o mesmo mês nos dois anos e consultar os números exatos."),
], columns=["Etapa", "Decisão", "Por quê"])


def pagina_metodologia() -> None:
    cabecalho("De onde vêm os dados e como foram tratados?")
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
            "- **Base:** planilha tratada da Sprint 2 com o tratamento de repetições (`dados_recife(5)`, aba "
            "*Entulhos tratados*). Os CSVs originais não foram alterados.")
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
            "- **Linha publicada:** uma linha dos arquivos do portal. O mesmo chamado pode aparecer em mais de um "
            "arquivo.\n"
            "- **Chamado:** linha que sobra depois de tirar as repetições (mesmo chamado em outro arquivo e mais "
            "de um chamado no mesmo endereço e dia). É a unidade de todo o painel. Não confirma descarte "
            "irregular.\n"
            "- **Endereço identificável:** rua, número com formato aceito e bairro reconhecido entre os 94 da "
            "referência oficial. SN, S/N, zero e números ambíguos ficam fora da comparação por endereço, mas "
            "continuam nas contagens por mês, bairro e RPA.\n"
            "- **Endereço recorrente:** endereço com chamados abertos em pelo menos N datas diferentes (padrão 3), "
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
            "sem filtros é **931 endereços**, igual à EDA da Sprint 3. Depois do tratamento de repetições eles "
            "somam **22,5%** dos chamados únicos (na EDA, 22,89% das linhas publicadas).")
        st.markdown("#### Próximos passos")
        st.markdown(
            "- Validar as coordenadas dentro do território do Recife e só então incluir o mapa.\n"
            "- Revisar com a fonte os endereços extremos e os endereços com chamados espalhados.\n"
            "- Confirmar com a Emlurb se vários chamados no mesmo endereço e dia são o mesmo pedido.")
        st.caption(f"Entrada: {META['entrada']} · SHA-256 {META['sha256_entrada'][:16]}…")

    st.divider()
    st.markdown("#### Histórico de decisões")
    st.dataframe(HISTORICO_DECISOES, hide_index=True, column_config={
        "Etapa": st.column_config.TextColumn(width=190),
        "Decisão": st.column_config.TextColumn(width="large"),
        "Por quê": st.column_config.TextColumn(width="large")})
    st.markdown("#### Baixar a base filtrada")
    st.markdown(f'<p class="nota">{fmt_int(len(DF))} chamados com os filtros atuais, com os campos originais '
                f'e os padronizados. A base derivada segue a licença ODbL: cite a fonte e compartilhe pela mesma '
                f'licença.</p>', unsafe_allow_html=True)
    colunas = ["id_fonte", "arquivo", "abertura", "situacao", "rua_informada", "numero_informado",
               "bairro_informado", "rua", "numero", "bairro", "rpa", "endereco_ok", "sem_coordenadas",
               "latitude", "longitude", "grupo_repeticao"]
    base_csv = DF[colunas].assign(abertura=DF["abertura"].dt.strftime("%d/%m/%Y"))
    baixar_csv(base_csv, "entulhos_recife_filtrado.csv", "Baixar base filtrada (CSV)", "dl_base")


# ---------------------------------------------------------------- navegação
PAG_VISAO = st.Page(pagina_visao_geral, title="Visão geral", icon=":material/dashboard:",
                    url_path="visao-geral", default=True)
PAG_REC = st.Page(pagina_recorrencia, title="Endereços que se repetem", icon=":material/repeat:", url_path="recorrencia")
PAG_TER = st.Page(pagina_territorio, title="RPAs e bairros", icon=":material/location_city:", url_path="territorio")
PAG_TEMPO = st.Page(pagina_tempo, title="Chamados por mês", icon=":material/calendar_month:", url_path="tempo")
PAG_QUAL = st.Page(pagina_qualidade, title="Qualidade dos dados", icon=":material/fact_check:",
                   url_path="qualidade")
PAG_MET = st.Page(pagina_metodologia, title="Fonte e método", icon=":material/info:", url_path="metodologia")

navegacao = st.navigation([PAG_VISAO, PAG_REC, PAG_TER, PAG_TEMPO, PAG_QUAL, PAG_MET], position="top")
navegacao.run()

st.divider()
st.caption("Fonte: Portal de Dados Abertos do Recife — Central de Atendimento de Serviços da Emlurb (156), licença ODbL. "
           "Tratamento e análise: equipe do Projeto 5 (Gestão Digital de Resíduos Sólidos Urbanos), CESAR School.")
