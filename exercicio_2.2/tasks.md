# tasks.md — Query Endpoint

> Derivado de: `plan.md` — Query Endpoint  
> Contexto: Azure Function HTTP trigger para RAG com Azure OpenAI + Azure AI Search  
> Convenção de tamanho: P = ≤2h · M = 2–4h · G = 4–8h

---

## TASK-001 — Scaffold da Azure Function HTTP Trigger

**Descrição**  
Criar a estrutura inicial da Azure Function v4 em TypeScript para o endpoint `POST /api/query`, incluindo handler, registro da função e configuração mínima de execução local.

**Critérios de aceite**
- Arquivo `src/functions/query.ts` existe e exporta a função registrada via `app.http()`
- `host.json` e `local.settings.json` configurados para Functions v4
- Endpoint responde `200 OK` com payload stub `{ answer: "ok" }` ao executar `func start` localmente
- Sem dependências de negócio implementadas (apenas scaffold)

**Dependências**  
Nenhuma — task inicial.

**Estimativa:** P

---

## TASK-002 — Validação de Input/Output com Zod

**Descrição**  
Definir e aplicar os schemas Zod para o corpo da requisição (`QueryRequest`) e para a resposta (`QueryResponse`), retornando `400 Bad Request` com mensagem de erro estruturada quando a validação falhar.

**Critérios de aceite**
- Schema `QueryRequest` valida: `question: string` (obrigatório, não-vazio)
- Schema `QueryResponse` valida: `answer: string`, `source_document: string`
- Requisição sem `question` retorna `400` com body `{ error: "validation_error", details: [...] }`
- Tipos TypeScript inferidos a partir dos schemas (sem duplicação manual de interfaces)
- Testes unitários dos schemas cobrem: campo ausente, string vazia, payload válido

**Dependências**  
TASK-001

**Estimativa:** P

---

## TASK-003 — Cliente Azure OpenAI para Geração de Embeddings

**Descrição**  
Implementar o módulo `src/clients/openaiClient.ts` responsável por converter a pergunta do atendente em embedding via Azure OpenAI, com retry e exponential backoff.

**Critérios de aceite**
- Função `getEmbedding(text: string): Promise<number[]>` exportada
- Usa `@azure/openai` SDK com credenciais via variáveis de ambiente (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`)
- Retry com exponential backoff: máximo 3 tentativas, delays 1s → 2s → 4s
- Lança erro tipado `EmbeddingError` após esgotar tentativas
- Testes unitários com mock do SDK: sucesso, falha com retry, falha após 3 tentativas

**Dependências**  
TASK-001

**Estimativa:** M

---

## TASK-004 — Cliente Azure AI Search para Busca Semântica

**Descrição**  
Implementar o módulo `src/clients/searchClient.ts` responsável por buscar os top-5 chunks mais relevantes no índice do Azure AI Search a partir do embedding gerado.

**Critérios de aceite**
- Função `searchChunks(embedding: number[]): Promise<Chunk[]>` exportada
- Tipo `Chunk` contém ao menos: `content: string`, `source_document: string`, `vigencia?: string`
- Busca retorna exatamente top-5 resultados (configurável via constante `TOP_K = 5`)
- Usa `@azure/search-documents` SDK com credenciais via variáveis de ambiente (`AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_API_KEY`, `AZURE_SEARCH_INDEX_NAME`)
- Retry com exponential backoff idêntico ao padrão de TASK-003
- Testes unitários com mock do SDK: sucesso com 5 chunks, índice vazio, falha com retry

**Dependências**  
TASK-001

**Estimativa:** M

---

## TASK-005 — Carregamento e Versionamento do System Prompt

**Descrição**  
Implementar o módulo `src/prompts/loader.ts` responsável por carregar o system prompt do arquivo `/prompts/system-prompt.md`, respeitando o context budget definido na ADR-0002 (~4K tokens para system prompt).

**Critérios de aceite**
- Função `loadSystemPrompt(): Promise<string>` exportada
- Lê de `/prompts/system-prompt.md` (caminho configurável via env `SYSTEM_PROMPT_PATH`)
- Valida que o prompt não excede 4.096 tokens (estimativa: `chars / 4`); lança `PromptBudgetError` se exceder
- Cache em memória após primeira leitura (não relê a cada invocação)
- Testes unitários: leitura bem-sucedida, exceção de budget, fallback de path

**Dependências**  
TASK-001

**Estimativa:** P

---

## TASK-006 — Montagem do Prompt com Context Budget

**Descrição**  
Implementar a função `src/prompts/builder.ts` que monta o prompt final para o GPT-4o combinando system prompt, chunks recuperados e pergunta do usuário, respeitando o context budget total definido na ADR-0002.

**Critérios de aceite**
- Função `buildPrompt(systemPrompt: string, chunks: Chunk[], question: string): PromptPayload` exportada
- Context budget respeitado: ~4K tokens (system) + ~8K tokens (chunks) + pergunta
- Chunks são truncados/priorizados por relevância se o budget de 8K for excedido (trunca os de menor score)
- Metadado de `vigencia` dos chunks é incluído no contexto quando presente (conforme ADR-0003)
- `PromptPayload` tipado com `messages: ChatMessage[]` pronto para envio ao SDK
- Testes unitários: budget dentro do limite, budget excedido com truncagem, chunks com vigência

**Dependências**  
TASK-004, TASK-005

**Estimativa:** M

---

## TASK-007 — Cliente GPT-4o para Geração de Resposta

**Descrição**  
Implementar o módulo `src/clients/completionClient.ts` responsável por enviar o prompt montado ao GPT-4o via Azure OpenAI e retornar a resposta textual.

**Critérios de aceite**
- Função `getCompletion(payload: PromptPayload): Promise<string>` exportada
- Usa deployment configurado via `AZURE_OPENAI_CHAT_DEPLOYMENT` (esperado: `gpt-4o`)
- Retry com exponential backoff: mesmo padrão de TASK-003
- Extrai apenas o texto da primeira `choice` da resposta
- Lança `CompletionError` tipado em caso de falha após retries
- Testes unitários com mock: resposta válida, timeout, falha após retries

**Dependências**  
TASK-003 (reutiliza padrão de cliente e retry)

**Estimativa:** M

---

## TASK-008 — Orquestração do Handler Principal

**Descrição**  
Conectar todos os módulos no handler da Azure Function (`src/functions/query.ts`), implementando o fluxo completo: validação → embedding → busca → montagem de prompt → completion → resposta.

**Critérios de aceite**
- Fluxo completo executado em sequência conforme o `plan.md`
- Resposta final segue schema `QueryResponse`: `{ answer: string, source_document: string }`
- `source_document` extraído do chunk de maior relevância retornado pelo Search
- Erros de cada cliente propagados como `500 Internal Server Error` com body `{ error: "internal_error" }` (sem vazar detalhes internos)
- Erro de validação (Zod) retorna `400`; demais erros retornam `500`
- Teste de integração local (sem mocks) com `func start` retorna resposta coerente para pergunta de exemplo

**Dependências**  
TASK-002, TASK-003, TASK-004, TASK-006, TASK-007

**Estimativa:** M

---

## TASK-009 — Structured Logging com Pino

**Descrição**  
Integrar o `pino` como logger estruturado em todos os módulos, garantindo rastreabilidade de cada etapa do fluxo sem vazar dados sensíveis.

**Critérios de aceite**
- Logger singleton exportado de `src/lib/logger.ts`
- Cada etapa do fluxo emite log estruturado com campos: `requestId`, `step`, `durationMs`
- Campos sensíveis omitidos dos logs: `question` (conteúdo), `embedding` (vetor), `apiKey`
- Nível de log configurável via env `LOG_LEVEL` (padrão: `info`)
- Em ambiente de teste (`NODE_ENV=test`) o logger não emite output (transport silencioso)
- Logs emitidos em formato JSON válido verificado por teste unitário simples

**Dependências**  
TASK-001

**Estimativa:** P

---

## TASK-010 — Configuração de Variáveis de Ambiente e Documentação de Deploy

**Descrição**  
Consolidar todas as variáveis de ambiente necessárias, criar o arquivo `.env.example` e documentar o processo de configuração para deploy no Azure.

**Critérios de aceite**
- `.env.example` contém todas as vars com descrição inline em comentário:
  - `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`, `AZURE_OPENAI_CHAT_DEPLOYMENT`
  - `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_API_KEY`, `AZURE_SEARCH_INDEX_NAME`
  - `SYSTEM_PROMPT_PATH`, `LOG_LEVEL`
- `local.settings.json` atualizado com todas as vars (valores placeholder)
- Seção "Environment Setup" adicionada ao `README.md` do projeto
- Nenhuma credencial real commitada (`.gitignore` validado)

**Dependências**  
TASK-008 (após o handler estar completo, o inventário de vars é definitivo)

**Estimativa:** P

---

## Resumo

| ID       | Descrição resumida                        | Tamanho | Depende de                          |
|----------|-------------------------------------------|---------|--------------------------------------|
| TASK-001 | Scaffold da Azure Function                | P       | —                                    |
| TASK-002 | Validação Zod (input/output)              | P       | TASK-001                             |
| TASK-003 | Cliente OpenAI — embeddings               | M       | TASK-001                             |
| TASK-004 | Cliente AI Search — busca top-5           | M       | TASK-001                             |
| TASK-005 | Carregamento do system prompt             | P       | TASK-001                             |
| TASK-006 | Montagem do prompt com context budget     | M       | TASK-004, TASK-005                   |
| TASK-007 | Cliente GPT-4o — completion               | M       | TASK-003                             |
| TASK-008 | Orquestração do handler principal         | M       | TASK-002, TASK-003, TASK-004, TASK-006, TASK-007 |
| TASK-009 | Structured logging com Pino               | P       | TASK-001                             |
| TASK-010 | Variáveis de ambiente e docs de deploy    | P       | TASK-008                             |

**Caminho crítico:** TASK-001 → TASK-004 → TASK-006 → TASK-008 → TASK-010
