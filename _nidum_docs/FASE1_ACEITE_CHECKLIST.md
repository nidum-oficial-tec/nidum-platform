# Fase 1 (2→7 coleções) — checklist de aceite (executar Davi + Claude, na volta)

> Executar **depois** de criar as 7 coleções, popular (dry-run aprovado → execução liberada),
> preencher `MAPA_COLECOES` e publicar o pipe 1.64.0. Antes disso, produção segue no 1.63.x.
> Ligar `DEBUG_TRECHOS=on` (UserValve, na própria sessão) para ver os trechos e a rota.

## A. Não-regressão de ranking (banco D1–D10)
Fonte das perguntas: `eval_ranking_fase0.md` (conjunto D1–D10).

| # | Pergunta | Critério de aceite |
|---|---|---|
| A1 | D1–D10 com `MAPA_COLECOES` preenchida | Nenhuma regressão vs. baseline 1.63.x; a resposta não degrada. |
| A2 | D10 (cronograma da Fazenda) | O `FAZ_Cronograma` (mais recente) aparece **acima** da doutrina FONTE. |
| A3 | D1/D3/D4/D5/D7 (conceituais) | FONTE continua dominando (não afundou por causa da seleção de coleções). |

## B. Roteamento por tipo (o que a Fase 1 muda)

| # | Pergunta / ação | Critério de aceite | Debug esperado |
|---|---|---|---|
| B1 | **Operacional sem FONTE:** "O que ficou pendente na reunião de 13/07?" | Resposta vem de atas/projetos; **zero trechos da FONTE**. | Coleções consultadas = `nd-atas`(+`nd-projetos`); nenhum trecho `FONTE >`. |
| B2 | **Conceitual pela FONTE:** "O que é intenção reta?" | Responde pela doutrina (FONTE). | Coleções = `nd-fonte`+`nd-normas`; trechos da FONTE presentes. |
| B3 | **Temporal/reunião:** pergunta com data ("...em 27/07") | Busca vai para `nd-atas`+`nd-projetos`. | Seleção temporal disparou. |
| B4 | **Rota errada de propósito** (pergunta que a heurística manda para a coleção errada) | A **rede de segurança** encontra a resposta assim mesmo. | Log/debug mostra `MAPA rede de seguranca -> 0 nas selecionadas; reexecuta nas N`. |
| B5 | **Sem duplicação:** qualquer pergunta | Um mesmo arquivo **não** aparece 2× (nova + antiga) no top-k. | As 2 coleções antigas **não** aparecem entre as consultadas. |
| B6 | **Procedência externa:** pergunta que puxa IPPUL (`nd-externo`) | A resposta **não** cita lei de Londrina como posição da Nidum. | *(etiqueta de procedência — PENDENTE no 1.64.0; ver 08. Por ora, conferir manualmente.)* |

## C. Ponta-a-ponta da esteira (adjustment #4)

| # | Ação | Critério de aceite |
|---|---|---|
| C1 | Colocar um **arquivo de teste novo** no SharePoint/repo (ex.: um cronograma `TESTE_Cronograma_...md` numa pasta de projeto) e deixar o fluxo normal rodar (puxar → converter → sincronizar). | O arquivo **aterrissa na coleção nova certa** (`nd-projetos`) — e no espelho das antigas durante a transição. |
| C2 | Colocar um arquivo **sem regra** (nome/pasta que não casam) | Cai em `nd-normas` **e** aparece no **resumo de sem-regra do summary do GitHub Action** (visível para revisão). *(depende de T4 — fiação do sincronizar.)* |
| C3 | Rodar `migrar_sete_colecoes.py` com `NIDUM_URL`+`NIDUM_TOKEN` (GET) | Confronto repo×produção fecha; a lista nominal do que existe só de um lado bate com o esperado. |

## D. Passos manuais de painel (o Davi executa — ver FASE1_PUBLISH_PREP.md)
- [ ] Criar as 7 coleções (anotar ids).
- [ ] Preencher `MAPA_COLECOES` (json papel→id).
- [ ] Confirmar `BASE_CONHECIMENTO_ID` = 2 ids antigos (rollback).
- [ ] Publicar pipe 1.64.0.
- [ ] Ensaiar o **rollback** (limpar `MAPA_COLECOES` → volta ao 1.63.x sem republish) antes de confiar.

## E. Saída (gate para fechar a fase)
- [ ] A + B + C verdes.
- [ ] Rollback ensaiado e instantâneo.
- [ ] Espelho com prazo: agendar o desligamento das antigas **após** este aceite (D19).
