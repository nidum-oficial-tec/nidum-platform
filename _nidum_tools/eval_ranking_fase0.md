# Conjunto de avaliacao de ranking — Fase 0

> Semente do banco de perguntas para **medir o rankeamento** (nao o roteamento).
> Fonte: `registro-tecnico/Registro Tecnico/12_Matriz_de_Perguntas_Reais.pdf`,
> `08_Cenarios_de_Teste.pdf`, `Gabarito_de_Cenarios.xlsx`. So o subconjunto que
> exercita a rota **documentos** entra aqui — perguntas de arquivo/imagem/saudacao
> nao tocam o RAG e ficam de fora.

## Para que serve

Medir, para cada pergunta, se **o documento certo entra no top-k** que a busca
entrega ao modelo. Sem numero, mudanca de ranking e chute (Fase 0, pre-requisito).

A metrica de baseline e simples: **taxa de acerto de top-k** = em quantas das N
perguntas o documento esperado apareceu entre os trechos recuperados. Depois de
cada mudanca (Fases 1-3), roda-se a mesma lista e compara-se a taxa.

## Como rodar o baseline (precisa da base VIVA)

Isto **nao roda offline** — precisa do Open WebUI de producao (base indexada,
embeddings, reranker). Passos:

1. Admin -> Functions -> ChatND -> Valves -> **`DEBUG_TRECHOS = on`**.
2. Para cada pergunta abaixo, mandar no chat como **admin**. O pipe exibe (status) e
   registra no log a lista de trechos recuperados, na ordem do reranker, com a nota.
3. Marcar na coluna **Resultado**: o documento esperado apareceu no top-k? (sim/nao)
   e em que posicao/nota.
4. Ao terminar, `DEBUG_TRECHOS = off`.

> Automacao futura: um harness pode chamar `POST /api/chat/completions`
> (`model: "chatnd"`) e ler os eventos `status` do SSE para capturar o relatorio sem
> a leitura manual. Fica para depois do baseline manual — a lista e curta.

## Lacuna a fechar antes/durante o baseline: nome do arquivo na base

A coluna **Documento esperado** abaixo esta no nivel abstrato dos PDFs de origem
("Documento Fundador v30", "Livro Empresas Vivas"). Para bater com o top-k e preciso
o **nome real do `.md` na base** (ex.: `FONTE > ...v30....md`). Esse mapa se levanta
uma vez, olhando a lista de arquivos das colecoes FONTE/ACERVOS (a mesma que o
`DEBUG_TRECHOS` mostra como `fonte=`). Preencher a coluna **Arquivo na base** na
primeira rodada e reusar nas seguintes.

## Perguntas (rota documentos)

| # | Pergunta (fala real) | Documento esperado (abstrato) | Colecao | Arquivo na base | Resultado |
|---|---|---|---|---|---|
| D1 | "O que e a Nidum?" | Documento Fundador (v30) | FONTE | _(preencher)_ | |
| D2 | "Qual a diferenca entre Fonte e convergencia?" | Fonte + glossario (16) | FONTE/ACERVOS | | |
| D3 | "O que e 'intencao reta'?" | Documento Fundador | FONTE | | |
| D4 | "Quem sao os ecossistemas e seus facilitadores?" | Documento Fundador | FONTE | | |
| D5 | "O que mudou da v29 para a v30?" | Fundadores v29 + v30 | FONTE | | |
| D6 | "O que e uma empresa viva?" | Livro Empresas Vivas | FONTE | | |
| D7 | "O que ja convergiu / o que esta em aberto na frente X?" | Convergencias (Em aberto) | ACERVOS | | |
| D8 | "Quais os ecossistemas da Nidum?" (F1) | Lista ancorada na Fonte | FONTE | | |
| D9 | "Isto esta alinhado a versao 30?" (F2) | v30 (etiqueta Fonte) | FONTE | | |
| D10 | "Como os ecossistemas interagem para gerar regeneracao?" | Raciocinio + Fonte (triade) | FONTE | | |

## Lacunas conhecidas (crescer com o uso real e com o motivo desta frente)

O motivo desta revisao e **mais volume + novas prioridades** (planilhas, assuntos
misturados). A semente acima nao cobre isso ainda. Ampliar com:

- **Planilhas (.xlsx):** perguntas cuja resposta e um valor/linha de uma planilha
  (ex.: "qual o status da etapa X no cronograma?"). Mede o problema do corte que perde
  o cabecalho da tabela — alvo da Fase 1b.
- **Recencia (versao nova x velha):** uma pergunta cuja resposta certa e a versao
  **recente** de um documento que tambem tem versao **antiga** na base. Mede o boost de
  recencia — alvo da Fase 3. So faz sentido quando houver o par na base.
- **Colheita continua:** a propria Matriz 12 manda ampliar com as perguntas reais do
  uso; as recorrentes com problema viram linha aqui.
