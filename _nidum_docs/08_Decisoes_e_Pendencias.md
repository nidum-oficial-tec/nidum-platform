# 08 — Decisões e Pendências

> **Para quem é:** quem retoma o projeto ou precisa decidir algo, e quer saber o que já foi decidido (e por quê) e o que ainda está em aberto.
> **Quando consultar:** antes de propor uma mudança de rumo ou reabrir uma discussão.

---

## Parte 1 — Decisões já tomadas (e o porquê)

| # | Decisão | Por quê |
|---|---|---|
| D1 | **Estender o fork do Open WebUI** (não criar do zero) | Reaproveita login, usuários, Storage, RAG, UI. Custo aceito: fork mais pesado de manter. |
| D2 | **Roteamento por um "motor invisível" (ChatND)** em vez de o usuário escolher o modelo | Simplicidade para o usuário; ele só vê uma IA, a da Nidum. |
| D3 | **RAG modo documento-inteiro** (não só trechos) | Trechos davam respostas fragmentadas/incompletas. Doc inteiro garante completude. Custo (~US$0,12/pergunta) aceito. |
| D4 | **Layout dos arquivos no código da ferramenta**, não em prompt | Garante identidade da marca consistente; prompt/RAG não estilizam arquivo. |
| D5 | **Wrappers privados + só a ChatND pública** | Usuário comum vê só a ChatND; motores ficam ocultos. |
| D6 | **Controle de acesso por aprovação manual** (não OAuth) | `nidumbrasil.com.br` não é Google Workspace; e-mails não são contas Google. Admin aprova só `@nidumbrasil.com.br`. |
| D7 | **Nunca revelar o LLM** ao usuário | Identidade: é "a inteligência da Nidum", não "OpenAI/Anthropic". |
| D8 | **Geração de imagem via Gemini** (`imagen-4.0-generate-001`, predict) | O modelo padrão do Open WebUI dava 404; este funciona com billing pago. |
| D9 | **Tríade fonte/forma/fluxo só quando aplicável** (gate no classificador) | Respostas pareciam "treinamento corporativo". A tríade é da própria Fonte (*Silêncio, Vida e Liberdade*), mas só cabe em pedidos gerativos. |
| D10 | **Editorial: estender o fork, headless (API+chat), Storage S3 ao escalar** | Precisa de endpoints/DB/jobs; livros estouram o volume de 500 MB. |
| D11 | **Editorial: evitar libs AGPL** (PyMuPDF, ebooklib) | Risco para uso comercial; EPUB é montado/lido com zipfile+XML. |
| D12 | **Continuidade: tudo no nome da empresa, chaves no Bitwarden** | A operação precisa sobreviver à saída de qualquer pessoa. |
| D13 | **Migração de e-mail adiada** | Tudo está no `nidum.tec26@gmail.com` (provisório) até haver e-mail institucional. Recomendação aceita: usar e-mail genérico de função, não pessoal. |
| D14 | **Ibrand para títulos** (além do logotipo) | Decisão do usuário (o brandbook reserva Ibrand ao logotipo, mas foi sobreposto); Ibrand tem cobertura PT completa. |
| D15 | **Base em 7 coleções por tipo** (`nd-atas`, `nd-projetos`, `nd-fonte`, `nd-normas`, `nd-marca`, `nd-contratos`, `nd-externo`), saindo de 2 (FONTE/ACERVOS) | Permite roteamento de busca por tipo (busca só nas coleções relevantes) e etiquetas de procedência. `nd-externo` isola docs públicos de terceiros (IPPUL: leis municipais). |
| D16 | **Regra de destino: CONTEÚDO decide, NOME confirma, PASTA desempata**; soberania de pasta `FONTE/`→`nd-fonte` e `IPPUL/`→`nd-externo` **acima** do conteúdo | Procedência inviolável (uma ata citada dentro da doutrina não vira `nd-atas`; lei de Londrina não entra em coleção interna). Fonte única: `esteira/_scripts/colecao_destino.py`. |
| D17 | **`cte_/ct_/cc_/ce_/ger_/ata_` → `nd-atas`** (ata de comitê); `cte_` **nunca** `nd-contratos` | `cte_` é Comitê Técnico (ata), não contrato. `nd-contratos` só por nome (contrato/acordo/estatuto/cnpj) ou pasta jurídica. |
| D18 | **Exclusão de indexação** (`testes/`, `Chico/1 - Cadastros`, backups `antes-da-correcao`, stubs <80 chars, OCR corrompido) — nada sai do repo | Gabaritos, dado pessoal e lixo não devem poluir a base; a exclusão é só de indexação, reversível. Sem-regra vai para `nd-normas` com warning visível. |
| D19 | **Espelho nas 2 coleções antigas tem PRAZO** | Durante a transição, arquivo novo é indexado na coleção nova **e** nas 2 antigas (rede de rollback). Após o aceite da fase, as antigas **param de RECEBER** novos; **nunca são apagadas**. |
| D20 | **Pasta = "projeto"** (instruções + coleções por pasta), com o seletor de Conhecimento do modal de Pasta restrito a **coleções** (prop `collectionsOnly`, PR #36, 2026-08-23) | O recurso já existia no fork (OWUI 0.9.6: `folder.data.system_prompt` + `files`, que o upstream chama de *Folder "Project" handling*) — não foi construído, foi habilitado. A restrição existe porque a pasta aponta para **coleção inteira, nunca para arquivo solto**: com a leitura liberada ao grupo, o `GET /knowledge/search/files` passou a listar um a um os arquivos das coleções no seletor. **CUSTOMIZAÇÃO DE CORE** (`Knowledge/KnowledgeSelector.svelte`, `Models/Knowledge.svelte`, `Folders/FolderModal.svelte`): vai conflitar em **todo bump de versão do fork** — ver a REGRA DO REBASE no `CLAUDE.md`. Pastas são **individuais** (tabela `folder` tem `user_id` e nenhum `access_control`); projeto compartilhado por equipe seria desenvolvimento novo. |
| D21 | **Coleções institucionais em Privado com grant de LEITURA ao grupo Coautores** (não públicas, não escrita) | O usuário seleciona e usa, mas não adiciona nem remove arquivo: todas as rotas de mutação (`/file/add`, `/file/remove`, `/{id}/update`, `/{id}/delete`, `/{id}/reset`) exigem `permission='write'`; o export é admin-only. **EFEITO ALÉM DO SELETOR:** o pipe chama `filter_accessible_collections` antes de buscar — quem ficar fora do grupo perde o RAG da rota `documentos` **em silêncio** (log `nenhuma colecao de conhecimento acessivel`, resposta genérica em vez de erro). Ao mexer nos grants, conferir a cobertura do grupo. |

## Parte 2 — Pendências que precisam de decisão ou ação

### Prioridade definida pelo usuário
1. ✅ **Separação de memória (Postgres)** — CONCLUÍDA em 2026-07-02 (Postgres + pgvector + R2). Ver [07_Diario_e_Status](07_Diario_e_Status.md).
2. 🟠 **Volume / billing do Railway** — o volume antigo segue montado como backup; avaliar desmontá-lo após período de segurança. Billing OK ($3/$20).
3. 🟡 **Grupos / permissionamento** — controle de acesso mais fino (plano esboçado: grupos Externo/Interno, base pública sem v30).

### Fase 1 (2→7 coleções) — status para o Davi (2026-08-18)
- 🟠 **Publish único** do ciclo Fase 1 (pipe 1.64.0 + fatia 1.63.2): criar as 7 coleções no painel, preencher `MAPA_COLECOES` (json papel→id) e `BASE_CONHECIMENTO_ID`, então publicar. Até lá produção roda a fatia antiga e `MAPA_COLECOES` vazia (dormente).
- ✅ **Etiquetas no contexto injetado** (procedência externa do `nd-externo`, `status=rascunho` do v31, `tipo=convergencia`) — implementadas no 1.64.0 (`_etiquetas_trecho`), entram no mesmo publish.
- ✅ **Fiação do `sincronizar.py`** (T4) — implementada (D-a/D-b/D-c): partição por `colecao_destino` + espelho + freio proporcional; dormente até trocar o `sync_config.json` pelo exemplo da Fase 1.
- 🟡 **Confronto repo × produção**: rodar `migrar_sete_colecoes.py` com `NIDUM_URL`+`NIDUM_TOKEN` (GET) para a lista nominal do que existe só de um lado (o Davi executa com credencial).
- 🟢 **`id vivo` de `BASE_CONHECIMENTO_ID`**: o default morto virou vazio; o id vivo mora no painel.
- 🟢 **`nd-fonte` = 9 obras canônicas** (decisão do Davi): FONTE é curada e pequena; a base nova espelha o repo. Os **61** arquivos legado da "ND Fonte" de produção (só em produção, não no repo) **não migram** — ficam na coleção antiga. Catálogo para revisão no fim do projeto: `esteira/_docs/FASE1_CATALOGO_LEGADO_FONTE.md` (grupo ⭐ = possível doutrina a trazer para o repo).
- ✅ **CORREÇÃO (2026-08-23) do item acima — os 61 JÁ ESTÃO no repo.** Conferência nome a nome (normalizando maiúsculas/pontuação): dos 61 listados no catálogo, **zero** estão ausentes do `FONTE/` do repo (hoje **72** `.md` = os 61 + 8 canônicas + 3 obras que chegaram depois do catálogo). Não foi migração manual: o `git log -- FONTE/` mostra só `puxar_sharepoint: carga automatica (delta)` — entraram no SharePoint e a esteira puxou pelo caminho certo. Cruzamento independente: o `_estado/sharepoint_delta.json` lista os mesmos 70. **Pendência que a conferência levantou:** as canônicas eram 9 e hoje são 8 — o `Nidum Documento Fundador - v31 (rascunho).md` foi removido do repo pela própria esteira (commit `ac3052e`), espelhando uma remoção no SharePoint. Confirmar se foi intencional. **Consequência:** a coleção antiga "ND Fonte - Fundadores" deixou de ser cópia única de qualquer coisa, o que remove o principal impedimento para aposentá-la (ver D19). O catálogo na esteira foi carimbado.
- 🟢 **Higiene (sem agir agora):** 4 comentários pré-existentes não-ASCII no `chatnd.py` (linhas ~298/329/411/1561) violam a convenção ASCII-only de `_nidum_tools/*.py`; antecedem a Fase 1. Corrigir no **próximo ciclo de manutenção do pipe**, não agora.

### Retenção de conversas (spec decidida 2026-07-02 — a IMPLEMENTAR)
- **Objetivo:** gestão de armazenamento.
- **Regra 1 — comprimir:** chat **sem interação há 7 dias** → comprimir o conteúdo para ocupar menos espaço.
- **Regra 2 — deletar:** chat **sem interação há 90 dias** → deletar o chat **+ os arquivos associados**.
- **Natureza:** funcionalidade nova de backend (Open WebUI não tem nativo) — job agendado sobre a tabela `chat` do Postgres, com **dry-run** antes de qualquer exclusão. A parte dos 90 dias é destrutiva → backup/confirmação.
- **Decisão em aberto:** "comprimir" = compressão real do conteúdo (exige o app descomprimir na leitura, mexe no fork) **ou** arquivar (nativo, mais simples). A decidir antes de implementar.

### Outras pendências em aberto
| Pendência | Natureza | Observação |
|---|---|---|
| **Default de `BASE_CONHECIMENTO_ID`** aponta para base morta (`f2c8a48c`) | Dívida técnica | Só funciona porque a valve sobrescreve para `a85d8a8f`. Alinhar o default no código. |
| **PDFs órfãos do v29/v30** (cópias fora da base do ChatND) | Decisão | Mantidos por regra `#não exclua nada`; remover só com OK explícito. |
| **`Capture001.png` (9,45 MB)** no volume | Decisão | Não removido (screenshot ambíguo, possível anexo de chat). |
| **Mecanismo de higiene de duplicados recorrente** | Implementação | **Desenhado** em `_nidum_manutencao/HIGIENE_DUPLICADOS.md`, não implementado (em stand-by por decisão do usuário). |
| **Editorial F3 — vínculo "modelo por projeto"** | Implementação + deploy | Núcleo da ficha pronto; falta o manifold no seletor. |
| **Editorial F2.4b — imagens nos exports** | Implementação | Embutir imagens com alt-text nos `.docx/.epub/.pdf`. |
| **`origin/main` atrás do main local** | Sincronização | Um deploy foi via `railway up` do local; sincronizar o GitHub com `git push origin main`. |
| **Repasse no roteador** (rota documentos sem trecho relevante deveria cair para diaadia) | Implementação | Hoje, sem contexto relevante, ainda manda para Documentos sem handoff. |
| **Sobreposição rápido × dia a dia** | Decisão | Fronteira tênue; usuário cogitou afiar ou fundir. |
| **SharePoint como fonte (auto-update)** | Projeto futuro | Exige app no Azure AD + Microsoft Graph + job de sync. |
| **Modelo guard de input/output** | Segurança | Recomendado antes de abrir uploads/conteúdo externo (injeção indireta). |
| **Pipe × arquivos da pasta** (D20) | Implementação | O middleware injeta os arquivos da pasta em `form_data['files']` a **cada** mensagem, e o `_anexos_recentes` não distingue origem. Três riscos: TRAVA 5 (anexo + transformação → rota `arquivo`) disparando sozinha; `MAX_CHARS_ANEXO` sendo pago em todo turno; e a regra "acervo pulado quando há anexo" desligando o RAG institucional em silêncio dentro de um projeto. Conserto proposto: marcar os arquivos vindos da pasta (cruzar ids com `folder.data['files']` via `__metadata__`) e tratá-los como canal próprio — "material do projeto" ≠ "anexo deste turno". **Medir antes de mexer** (log: `classificador=`, `chars_acervo`, linha "COM anexo"). |

> Conforme as decisões forem tomadas, mover da Parte 2 para a Parte 1 (com a data e o porquê).
