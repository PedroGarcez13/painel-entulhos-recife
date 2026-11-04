# Painel — Remoção de Entulhos no Recife (Central 156)

Entregável 4 do Projeto 5 (CC · Análise e Visualização de Dados): **Dashboard Interativo — Versão Inicial**.

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
        │  Sprint 2: Python + planilha
        ▼
dados/entrada/dados_recife(4).xlsx  (aba "Entulhos tratados") ← dado tratado
        │  python preparar_dados.py
        ▼
dados/painel/entulhos_painel.parquet + metadados.json      ← dado do painel
        │  streamlit run app.py
        ▼
Painel (filtros → indicadores, gráficos e tabelas)
```

`preparar_dados.py` não altera a entrada. Ele converte tipos, mantém só as colunas usadas e confere as
contagens da Sprint 2: 21.646 entulhos, 20.300 no recorte, 17.134 com endereço suficiente, 10.929 sem
coordenadas e 1.218 no mesmo endereço e dia. Se algum número divergir, o script para sem gerar o painel.
Se a planilha da Sprint 2 for atualizada, substitua o XLSX em `dados/entrada/` e rode o script de novo.

## Estrutura

| Arquivo | Função |
|---|---|
| `app.py` | Interface Streamlit: filtros, indicadores, abas e gráficos (Plotly). |
| `calculos.py` | Regras de cálculo (recorrência, séries, contagens, qualidade), sem interface. |
| `preparar_dados.py` | Gera a base do painel a partir da planilha tratada. |
| `tests/test_numeros_eda.py` | Confere se o painel sem filtros reproduz os números da EDA da Sprint 3. |
| `.streamlit/config.toml` | Tema claro e cores do painel. |

Rodar os testes: `python tests/test_numeros_eda.py`

## O que o painel tem

- **Filtros na barra lateral**, aplicados a tudo: período de abertura (mês a mês), RPA, bairro (a lista
  acompanha as RPAs escolhidas), situação registrada, arquivo de origem e o mínimo de dias distintos para
  considerar recorrência (padrão 3). Há um botão para limpar os filtros.
- **Indicadores:** registros, endereços recorrentes, participação desses endereços, mês de pico e
  percentual sem coordenadas.
- **Recorrência:** distribuição de dias distintos por endereço (com destaque do limiar), os 10/20/30
  endereços com mais dias, tabela pesquisável e o histórico de datas de um endereço ao clicar na linha.
- **Território:** bairros e RPAs, por registros ou por endereços recorrentes.
- **Tempo:** série mensal empilhada por arquivo de origem, com o período de cobertura limitada sombreado.
- **Qualidade dos dados:** coordenadas por arquivo e quadro de problemas com a decisão tomada.
- **Sobre os dados:** fonte, licença, definições, o que o painel não afirma e próximos passos.
- Cada tabela pode ser baixada em CSV (separador `;`, decimal `,`, compatível com Excel em português).

## Regras de cálculo (iguais às da EDA)

- **Registro** = linha publicada (não é protocolo único).
- **Endereço** = rua padronizada + número padronizado + bairro de referência, apenas quando
  "Endereço permite comparação?" = Sim.
- **Recorrência** = quantidade de datas de abertura distintas por endereço. Vários chamados no mesmo dia
  contam um dia. O limiar 3 é regra preliminar do projeto, não definição oficial da Emlurb.
- **Bairro** sem correspondência na referência → `NÃO INFORMADO`. A **RPA** usada é a informada, para não
  perder esses 7 registros.

Sem filtros, o painel reproduz a EDA: 931 endereços com 3 ou mais dias (de 11.556), que somam 4.646
registros (22,89% do recorte). O maior caso é RUA CORONEL OLIVEIRA, 53 – AFOGADOS, com 71 dias. COHAB tem
1.217 registros, a RPA 6 tem 4.680 e o mês de pico é dez/2024, com 1.669.

> A SR1 citava 1.288 endereços / 27,8%. O critério daquele cálculo não está documentado e não pôde ser
> reproduzido sobre a base tratada. O painel usa a regra documentada acima.

## Decisões visuais

- Uma cor (azul) para séries únicas. Três cores fixas para os arquivos de origem (azul, laranja,
  verde-água), sempre na mesma ordem, mesmo com filtros. É uma combinação segura para daltonismo.
- Cinza para o que está abaixo do limiar de recorrência, deixando o destaque nos endereços recorrentes.
- Grade fina só no eixo de valores, rótulos diretos nas barras e tooltip em todas as marcas.
- Cada gráfico tem: a pergunta, a leitura gerada a partir dos dados filtrados e o limite da interpretação.
- **Sem mapa nesta versão:** 53,8% dos registros não têm coordenadas, e as existentes ainda não foram
  validadas dentro do território do Recife.

## Publicação (próximo entregável)

O painel roda no Streamlit Community Cloud sem mudanças: suba esta pasta para um repositório no GitHub
e aponte o deploy para `app.py`.

## Fonte e licença

Portal de Dados Abertos do Recife — Central de Atendimento de Serviços da Emlurb (156):
https://dados.recife.pe.gov.br/dataset/central-de-atendimento-de-servicos-da-emlurb-156
Licença ODbL (Open Database License): atribuição obrigatória e compartilhamento pela mesma licença.
