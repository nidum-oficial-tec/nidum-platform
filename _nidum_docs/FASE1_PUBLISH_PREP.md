# Fase 1 (2→7 coleções) — preparação do PUBLISH (não mergear no HTML antes do deploy)

> **REGRA DA DOC:** este arquivo é PREPARAÇÃO. As entradas abaixo entram na
> `Documentacao_ChatND_Nidum.html` (doc de produção) **no momento do publish**, não antes.
> Enquanto não publicado, produção roda a fatia antiga e `MAPA_COLECOES` vazia.

## Passos de painel (o Davi executa — nada disso é automatizável pela linha vermelha)

1. **Criar as 7 coleções** no painel (Knowledge): `nd-atas`, `nd-projetos`, `nd-fonte`,
   `nd-normas`, `nd-marca`, `nd-contratos`, `nd-externo`. Anotar o id de cada uma.
2. **Popular** (após aprovar o dry-run): rodar `migrar_sete_colecoes.py` já com a execução
   liberada (fase seguinte — hoje só `--dry-run`).
3. **Valve `MAPA_COLECOES`** (Admin → Functions → ChatND → Valves): colar o json papel→id
   (o `migrar_sete_colecoes.py` imprime o template com placeholders):
   ```json
   {"atas":"<id>","projetos":"<id>","fonte":"<id>","normas":"<id>",
    "marca":"<id>","contratos":"<id>","externo":"<id>"}
   ```
4. **Valve `BASE_CONHECIMENTO_ID`**: manter os 2 ids antigos (FONTE, ACERVOS) durante a
   transição — são o rollback. (Com `MAPA_COLECOES` preenchida, a busca ignora as antigas;
   elas só existem para o rollback.)
5. **Publicar o pipe** 1.64.0 via API (`publicar_pipe.py`) — só depois do aceite.

## Entradas para a `Documentacao_ChatND_Nidum.html` (colar no publish)

- **Seção 1 (versão):** ChatND `1.64.0`.
- **Histórico de alterações (nova linha no topo):**
  `1.64.0 | pipe | MAPA_COLECOES: busca por tipo em 7 coleções (fonte+normas p/ conceitual;
  atas+projetos p/ temporal; senão as 7), 2 antigas só p/ rollback; rede de segurança
  (0 trechos → todas); BASE_CONHECIMENTO_ID morto→vazio. Validar: teste_mapa_colecoes.py +
  16/16 do pipe; com MAPA vazia o comportamento é idêntico ao 1.63.x.`

## Procedimento de ROLLBACK (documentar junto do publish)

O rollback **não exige republish** (valves são lidas do banco a cada request):

1. **`MAPA_COLECOES` → vazia** (limpar a valve). O pipe volta ao comportamento atual: busca
   em `BASE_CONHECIMENTO_ID` (as 2 coleções antigas), sem seleção por tipo.
2. **`BASE_CONHECIMENTO_ID`** já está nos 2 ids antigos → nada a mudar.
3. As 7 coleções novas **continuam existindo** (nunca se apaga nada); só deixam de ser
   consultadas. As 2 antigas **nunca saíram do lugar** e seguiram recebendo os arquivos novos
   (espelho da transição), então estão íntegras.

Tempo de rollback: segundos (só limpar uma valve no painel). Sem downtime, sem deploy.

## Espelho com prazo (D19)

Enquanto o espelho está ligado, arquivo novo entra na coleção nova **e** nas 2 antigas.
**Após o aceite da fase**, desligar o espelho (as antigas param de RECEBER novos); elas
**nunca são apagadas** — ficam congeladas como rede de rollback.
