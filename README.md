# Painel — Remoção de Entulhos no Recife (Central 156)

Projeto 5 (CC · Análise e Visualização de Dados). Versão revisada após o retorno do professor sobre o
Dashboard Consolidado (entregável 6).
Publicado em https://entulhos-recife-156.streamlit.app/

O painel responde às três perguntas do projeto para quem acompanha a limpeza urbana:

1. **Onde os chamados se repetem?** Endereços com chamados em vários dias distintos.
2. **Onde os registros se concentram?** Bairros e RPAs.
3. **Como variam no tempo?** Série mensal separada pelo arquivo de origem.

Ele também mostra a qualidade dos dados e as limitações de cada leitura.
Chamados registrados **não confirmam** descarte irregular nem pontos críticos oficiais.

## Como executar

```bash
pip install -r requirements.txt
streamlit run app.py
```

O painel abre em `http://localhost:8501`. A base do painel já está em `dados/painel/`.

## Pipeline de dados

```
CSVs originais da Central 156 (2024, 2025, 2026)          ← dado bruto, preservado
        │  Sprint 2: Python + planilha (os três arquivos juntos)
        ▼
dados/entrada/dados_recife(4).xlsx  (aba "Entulhos tratados") ← dado tratado da Sprint 2
        │  python tratar_repeticoes.py
        ▼
dados/entrada/dados_recife(5).xlsx  (+ colunas e aba "Repetições") ← repetições marcadas
        │  python preparar_dados.py
        ▼
dados/painel/entulhos_painel.csv.gz + metadados.json       ← dado do painel
        │  streamlit run app.py
        ▼
Painel (filtros → indicadores, gráficos e tabelas)
```

Nenhum script altera a entrada. `preparar_dados.py` confere as contagens da Sprint 2 (21.646 entulhos,
20.300 no recorte, 17.134 com endereço suficiente, 10.929 sem coordenadas, 1.218 no mesmo endereço e dia)
e do tratamento de repetições (19.643 chamados únicos). Se algum número divergir, o script para.

## Mapa

Contornos: [Bairros do Recife](https://dados.recife.pe.gov.br/dataset/area-urbana), GeoJSON oficial da
Prefeitura (licença ODbL), simplificado em ~5 m por `python preparar_mapa.py bairros-do-recife.geojson`
(47.762 → 5.273 pontos, 133 KB; concorda em 99,9% com o original no teste de ponto em polígono).

- A cor usa o **bairro informado** no chamado, então entram também os 54,7% sem coordenadas.
- "Chamados por km²" divide pela área do bairro: por volume a RPA 6 lidera; por área, a RPA 2
  (232 chamados/km², o dobro das outras).
- `preparar_dados.py` confere cada coordenada com o mapa: 89,3% caem no bairro informado, 10,0% em outro
  bairro (em geral vizinho) e 0,6% fora do Recife. Os pontos do mapa usam só as que caem no próprio bairro.
- O mapa de fundo é o Carto Positron (gratuito, sem chave), carregado pelo Plotly.

## Tratamento de repetições

O "Identificador na fonte" é só a numeração da linha em cada CSV (o mesmo número aparece nos três arquivos
com chamados diferentes), então a repetição é identificada pelo conteúdo, depois de juntar os arquivos:

1. **Mesmo chamado em outro arquivo:** mesma data de abertura e mesma rua, número e bairro informados, em
   arquivos diferentes (quase sempre um chamado de 2024 republicado no arquivo de 2025). Conta uma vez.
2. **Mesmo endereço e dia:** com endereço identificável, mesma rua, número e bairro padronizados na mesma
   data. Conta como uma ocorrência.

Fica a linha com coordenadas; empatando, a do arquivo mais recente. As outras continuam na planilha com
"Conta como chamado único?" = Não. No recorte 2024–2025: 20.300 linhas → −266 republicadas → −391 no mesmo
endereço e dia → **19.643 chamados únicos**, que são a base de todo o painel.

## Estrutura

| Arquivo | Função |
|---|---|
| `app.py` | Interface Streamlit: filtros, navegação por páginas, indicadores e gráficos (Plotly). |
| `calculos.py` | Regras de cálculo (recorrência, séries, contagens, qualidade), sem interface. |
| `preparar_mapa.py` | Simplifica o GeoJSON oficial de bairros e gera `dados/geo/bairros_recife.geojson`. |
| `geo.py` | Ponto em polígono, simplificação e área, só com numpy. |
| `tratar_repeticoes.py` | Marca as repetições na planilha e gera a `dados_recife(5).xlsx`. |
| `preparar_dados.py` | Gera a base do painel a partir da planilha tratada. |
| `tests/test_numeros_eda.py` | Confere os números sem filtros: EDA da Sprint 3 e base sem repetições. |
| `.streamlit/config.toml` | Tema claro e cores do painel. |

Rodar os testes: `python tests/test_numeros_eda.py`

## O que o painel tem

Sete páginas na barra superior, todas com o mesmo modelo: pergunta como título → indicadores → gráfico →
leitura com o número → limite da interpretação → tabela e download.

| Página | Pergunta | Conteúdo |
|---|---|---|
| Visão geral | O que o painel mostra? | Três achados recalculados pelo filtro, com link para a página de cada um. |
| Mapa | Onde estão os chamados no mapa do Recife? | Bairros ou RPAs pintados por chamados, chamados por km² ou endereços recorrentes; pontos dos endereços recorrentes. |
| Endereços que se repetem | Quais endereços pedem remoção de entulho várias vezes? | Endereços recorrentes por faixa de dias, os 10 com mais dias, conferência dos endereços com as coordenadas e histórico de um endereço. |
| RPAs e bairros | Quais RPAs e bairros concentram os chamados? | Primeiro as 6 RPAs e o bairro que mais pesa em cada uma; depois os bairros dentro da RPA escolhida. |
| Chamados por mês | Quantos chamados há em cada mês? | Uma linha por ano (jan–dez) e tabela meses × anos. |
| Qualidade dos dados | Os dados são confiáveis? | Tratamento de repetições, coordenadas por arquivo e quadro de problemas com a decisão. |
| Fonte e método | De onde vêm os dados e como foram tratados? | Fonte, licença, definições, histórico de decisões e download da base filtrada. |

- **Filtros na barra lateral**, aplicados a todas as páginas e mantidos ao trocar de página.
- Se um filtro não retorna chamados, a página avisa e sugere ampliar o período.
- Cada tabela pode ser baixada em CSV (separador `;`, decimal `,`, compatível com Excel em português).

## Regras de cálculo (iguais às da EDA)

- **Chamado** = linha que sobra depois do tratamento de repetições (não confirma descarte irregular).
- **Endereço** = rua padronizada + número padronizado + bairro de referência, apenas quando
  "Endereço permite comparação?" = Sim.
- **Recorrência** = quantidade de datas de abertura distintas por endereço. Vários chamados no mesmo dia
  contam um dia. O limiar 3 é regra preliminar do projeto, não definição oficial da Emlurb.
- **Bairro** sem correspondência na referência → `NÃO INFORMADO`. A **RPA** usada é a informada, para não
  perder esses 7 registros.

Sem filtros: 19.643 chamados; 931 endereços com 3 ou mais dias (de 11.556, igual à EDA), que somam 4.416
chamados (22,5%). O maior caso é RUA CORONEL OLIVEIRA, 53 – AFOGADOS, com 71 dias. A RPA 6 tem 4.592
chamados e, dentro dela, COHAB pesa mais (1.192). O mês com mais chamados é dez/2024, com 1.474. Em 97,5%
dos 488 endereços recorrentes com coordenadas, os chamados ficam a até 100 m do centro do endereço.

> A SR1 citava 1.288 endereços / 27,8%. O critério daquele cálculo não está documentado e não pôde ser
> reproduzido sobre a base tratada. O painel usa a regra documentada acima.

## Decisões visuais

- Uma cor (azul) para séries únicas. Três cores fixas para os arquivos de origem (azul, laranja,
  verde-água), sempre na mesma ordem, mesmo com filtros. É uma combinação segura para daltonismo.
- Cinza para o que está abaixo do limiar de recorrência, deixando o destaque nos endereços recorrentes.
- Grade fina só no eixo de valores, rótulos diretos nas barras e tooltip em todas as marcas.
- Cada gráfico tem: a pergunta, a leitura gerada a partir dos dados filtrados e o limite da interpretação.
- **Mesmo modelo em todas as páginas** e uma Visão geral na entrada: o resumo vem antes do detalhe.
- **Sem mapa nesta versão:** 53,8% dos registros não têm coordenadas, e as existentes ainda não foram
  validadas dentro do território do Recife.

## Publicação

Streamlit Community Cloud, a partir deste repositório (arquivo principal `app.py`). Cada push na branch
principal atualiza o painel publicado. No plano gratuito o app "dorme" após dias sem acesso e leva cerca de
30 segundos para acordar: abra o link antes de apresentar.

## Fonte e licença

Portal de Dados Abertos do Recife — Central de Atendimento de Serviços da Emlurb (156):
https://dados.recife.pe.gov.br/dataset/central-de-atendimento-de-servicos-da-emlurb-156
Licença ODbL (Open Database License): atribuição obrigatória e compartilhamento pela mesma licença.
