# Interação — Análise Técnica RAG para NovaTech × DB1

> **Registro completo da conversa:** contexto fornecido pelo usuário + análise técnica gerada.  
> **Data:** Junho 2026

---

## Prompt do Usuário

### Cenário

> A NovaTech é uma empresa de médio porte do setor de logística com 1.200 funcionários. Sua operação depende de um conjunto extenso de documentação interna: manuais de procedimento operacional, políticas de compliance, tabelas de SLA por tipo de cliente, regras de cálculo de frete, e normas de segurança de carga.
>
> Hoje, essa documentação está espalhada em três fontes: um SharePoint corporativo com ~800 documentos (PDFs e Word), uma wiki interna no Confluence com ~400 páginas, e uma pasta de rede com planilhas de referência atualizadas mensalmente. O problema: a equipe de atendimento ao cliente (45 pessoas) gasta em média 12 minutos por chamado buscando informações nessas fontes para responder dúvidas de clientes sobre prazos, regras de frete, políticas de devolução e procedimentos de reclamação. Isso gera atrasos, respostas inconsistentes e frustração tanto dos atendentes quanto dos clientes.
>
> A NovaTech contratou a DB1 para construir um assistente de IA que permita aos atendentes fazer perguntas em linguagem natural e receber respostas fundamentadas na documentação oficial da empresa, com indicação da fonte. O assistente será integrado ao ambiente Microsoft da NovaTech (Teams + SharePoint).

**Informações adicionais fornecidas pela NovaTech:**

- O volume médio é de 320 chamados/dia, dos quais ~60% envolvem consulta a documentação.
- A documentação é atualizada mensalmente por 3 áreas diferentes (Operações, Compliance, Comercial), sem processo unificado de revisão.
- Alguns documentos se contradizem entre versões — a equipe de atendimento hoje resolve isso "perguntando para quem sabe".
- A NovaTech já tem licenças Microsoft 365 E3 e está disposta a provisionar Azure AI Services.
- O projeto tem orçamento para 3 meses de discovery + desenvolvimento + go-live.
- A expectativa da diretoria é reduzir o tempo médio de busca de 12 para menos de 2 minutos por chamado.

### Informações Técnicas Adicionais

> Os PDFs do SharePoint incluem documentos com tabelas complexas (tabelas de frete com 15+ colunas), fluxogramas embutidos como imagens, e alguns documentos escaneados (OCR necessário). A wiki do Confluence tem links internos entre páginas e usa macros customizadas. As planilhas têm fórmulas interdependentes.

> **Conceito de context engineering aplicado a RAG:** O contexto que o LLM recebe a cada pergunta é limitado pela janela de contexto do modelo. A qualidade da resposta depende de: quais chunks são selecionados (relevância), quantos chunks cabem no contexto (orçamento de atenção), onde ficam posicionados no prompt (informação no meio de contextos longos é "esquecida" — o efeito "lost in the middle"), e o que mais está no contexto competindo por atenção (system prompt, histórico de conversa, instruções).

### Solicitação

Produzir uma análise técnica que cubra:

- Para cada tipo de fonte (PDFs com tabelas, PDFs escaneados, wiki com links, planilhas com fórmulas): qual o desafio para o pipeline de RAG, como isso afeta a qualidade das respostas, e uma estratégia de tratamento.
- Estimativa do tamanho aproximado da base em tokens considerando ~800 documentos PDF (média de 10 páginas cada), ~400 páginas wiki (média de 1.500 palavras cada), e ~50 planilhas. Use a regra prática de ~0,75 palavras por token.
- Análise de orçamento de contexto: dado que o GPT-4o tem 128K tokens de janela e o system prompt + instruções consomem ~2K tokens, quantos chunks de ~500 tokens cabem em cada query? Como isso afeta a estratégia de chunking e retrieval?
- Recomendação de estratégia de chunking justificada pelo tipo de pergunta que o usuário fará e pelo conceito de lost in the middle.

---

## Resposta — Análise Técnica

# Análise Técnica — Pipeline RAG para NovaTech
**Projeto:** Assistente de IA para Atendimento ao Cliente  
**Cliente:** NovaTech · **Contratada:** DB1  
**Data:** Junho 2026 · **Versão:** 1.0

---

### Sumário Executivo

A NovaTech possui aproximadamente **4,2 milhões de tokens** de documentação distribuídos entre PDFs, wiki e planilhas — o que torna inviável qualquer abordagem de contexto estático. Um pipeline RAG bem calibrado é a única estratégia viável para atingir a meta de resposta em menos de 2 minutos. Este documento detalha os desafios por tipo de fonte, os cálculos de orçamento de contexto e as estratégias de chunking recomendadas.

---

### 1. Análise por Tipo de Fonte

#### 1.1 PDFs com Tabelas Complexas (tabelas de frete com 15+ colunas)

**Desafio para o pipeline RAG**

Extratores de PDF genéricos (PyMuPDF, pdfplumber) serializam tabelas como texto contínuo, destruindo a relação entre cabeçalho de coluna e valor de célula. Uma tabela com 15 colunas e 80 linhas vira um bloco de ~1.200 tokens onde a informação estrutural é perdida. O LLM recebe um chunk como:

```
Cliente_A Regional_SP Prazo_3d Frete_R$45 Seguro_1% ... [linha 2] Cliente_B ...
```

sem saber que `R$45` corresponde à coluna `Frete_Padrão` e não à coluna `Frete_Expresso`.

**Impacto na qualidade das respostas**

Respostas com valores trocados entre colunas adjacentes — o modelo confabula a relação linha/coluna. Perguntas como *"qual o prazo para cliente Tier 2 na região Sul com frete expresso?"* exigem intersecção de linha + coluna, que texto serializado ingênuo não preserva.

**Estratégia de tratamento**

1. **Extração estruturada:** usar `camelot` ou `pdfplumber` para detectar e extrair tabelas como DataFrames antes do chunking.
2. **Serialização semântica por linha:** cada linha da tabela vira um documento independente com todos os cabeçalhos explicitados:
   ```
   [TABELA: Frete por Região] Cliente_Tier: 2 | Região: Sul | Modalidade: Expresso | Prazo: 24h | Valor: R$78,00 | Seguro: 1,5%
   ```
3. **Metadados de proveniência:** nome do documento, número da página, nome da tabela — para citação de fonte na resposta.
4. **Fallback visual (tabelas escaneadas):** para tabelas embutidas como imagem, usar GPT-4o Vision ou Azure Document Intelligence para extração OCR + estrutura.

---

#### 1.2 PDFs Escaneados (OCR necessário)

**Desafio para o pipeline RAG**

Documentos escaneados não possuem camada de texto. OCR nativo de qualidade baixa gera ruído léxico grave: `"prazo de entrega"` pode virar `"praz0 de entrcga"`. Isso degrada o embedding — o vetor semântico do chunk é distorcido — e o retrieval falha para queries que dependem exatamente dessas palavras.

**Impacto na qualidade das respostas**

Falsos negativos no retrieval: o chunk correto existe no índice mas não é recuperado porque sua representação vetorial foi corrompida pelo OCR. O atendente pergunta algo que está no documento e o assistente responde "não encontrei informações" — pior do que o cenário atual.

**Estratégia de tratamento**

1. **Pré-processamento com Azure Document Intelligence (Form Recognizer):** suportado pelas licenças E3 + Azure AI Services já provisionados pela NovaTech. Extrai texto com confiança por palavra e sinaliza blocos de baixa confiança.
2. **Filtro de qualidade OCR:** rejeitar chunks com score médio de confiança < 80% e sinalizar o documento para revisão humana.
3. **Post-processing de normalização:** spell-checker com dicionário customizado do domínio logístico (termos como "RNTRC", "CTE", "ANTT") para corrigir erros sistemáticos de OCR.
4. **Identificação e catalogação:** manter lista de documentos escaneados na camada de metadados para priorizar reprocessamento quando forem digitalizados na origem.

---

#### 1.3 Wiki Confluence com Links Internos e Macros

**Desafio para o pipeline RAG**

Páginas wiki são frequentemente **fragmentadas por design**: a resposta completa para uma pergunta está distribuída entre a página principal + 3 páginas linkadas. Chunks de uma única página ficam semanticamente incompletos. Macros customizadas do Confluence (expand, panel, jira-issues) geram lixo HTML no export e precisam ser removidas antes do embedding. Links internos do tipo `[ver política de devolução|/wiki/x/123]` perdem significado fora do contexto da wiki.

**Impacto na qualidade das respostas**

O modelo recebe um chunk que diz *"conforme descrito na política de devolução (ver link)"* sem ter acesso ao conteúdo da página linkada — resposta incompleta ou evasiva. Macros não tratadas inserem tokens de ruído que diluem o sinal semântico do embedding.

**Estratégia de tratamento**

1. **Export via API REST do Confluence** (não export HTML manual): usar a API v2 para extrair conteúdo em formato storage (XML estruturado) e converter para Markdown limpo com `atlassian-python-api` + `markdownify`.
2. **Resolução de links internos:** no momento do processamento, seguir links internos até 1 nível de profundidade e incluir um resumo da página linkada como contexto no chunk pai (inline context injection).
3. **Strip de macros:** regex + parser XML para remover macros antes da indexação, preservando apenas o texto visível.
4. **Chunking por seção semântica:** usar os headers H1/H2/H3 como delimitadores naturais de chunk — respeita a estrutura editorial da wiki.

---

#### 1.4 Planilhas com Fórmulas Interdependentes

**Desafio para o pipeline RAG**

Planilhas não são documentos de texto — são **modelos de cálculo**. Uma planilha de cálculo de frete pode ter a célula `F15 = B15 * VLOOKUP(C15, TabelaZonas, 3, FALSE) * (1 + TaxaSeguro)`. O valor final só existe em tempo de execução; o texto extraído é `=B15*VLOOKUP(...)`, não `R$145,00`. Além disso, dependências entre abas criam contexto invisível: a resposta correta para *"quanto custa frete para Manaus?"* pode depender de valores em 3 abas diferentes.

**Impacto na qualidade das respostas**

O LLM não executa fórmulas. Se o pipeline indexar fórmulas como texto, o modelo vai tentar interpretar a sintaxe do Excel como linguagem natural e produzir respostas incorretas ou inventadas.

**Estratégia de tratamento**

1. **Execução das planilhas antes da indexação:** usar `openpyxl` + `xlcalculator` (ou exportar para CSV via Excel automation) para calcular e materializar os valores finais de todas as células.
2. **Indexar valores + contexto de rótulo:** cada valor relevante é indexado com seu rótulo de linha + coluna:
   ```
   [PLANILHA: Tabela_Frete_2025-06] Origem: SP | Destino: AM | Peso: até 10kg | Modalidade: Rodoviário | Valor: R$ 312,00
   ```
3. **Snapshot mensal versionado:** como as planilhas são atualizadas mensalmente, implementar pipeline automatizado de reprocessamento com versionamento — manter versão atual + 1 versão anterior para auditoria.
4. **Documentar dependências:** mapear as dependências entre abas para garantir que o snapshot capture o estado completo e consistente de cada planilha.

---

### 2. Estimativa do Tamanho da Base em Tokens

| Fonte | Qtd. | Volume bruto | Palavras estimadas | Tokens estimados |
|-------|------|-------------|-------------------|-----------------|
| PDFs (800 docs × 10 pág.) | 8.000 páginas | ~300 palavras/pág.¹ | 2.400.000 | **3.200.000** |
| Wiki Confluence (400 páginas) | 400 páginas | 1.500 palavras/pág. | 600.000 | **800.000** |
| Planilhas (50 × 5 abas × ~200 células úteis × ~3 palavras/célula) | 50 planilhas | serialização texto | 150.000 | **200.000** |
| **TOTAL** | | | **3.150.000** | **~4,2 M tokens** |

> ¹ Documentos técnicos com tabelas, listas e margens têm densidade menor que texto corrido. 300 palavras/página é estimativa conservadora.  
> Regra aplicada: `tokens = palavras ÷ 0,75`

**Interpretação**

- **4,2 M tokens** é cerca de **33 vezes** a janela de 128K do GPT-4o.
- Todo o corpus jamais pode ser enviado em um único prompt — RAG com retrieval seletivo é obrigatório, não opcional.
- O índice vetorial (embeddings + metadados) ocupará aproximadamente **630 MB** a 1.536 dimensões float32 (padrão `text-embedding-3-large`), bem dentro da capacidade do Azure AI Search.

---

### 3. Análise do Orçamento de Contexto

#### 3.1 Partição da Janela (GPT-4o, 128K tokens)

```
┌─────────────────────────────────────────────────────────────┐
│                  JANELA: 128.000 tokens                      │
├─────────────────────────────────────────────────────────────┤
│  System prompt + instruções RAG        ~2.000 tokens  ( 2%) │
│  Reserva para output gerado            ~4.000 tokens  ( 3%) │
│  Histórico de conversa (2-3 turnos)    ~2.000 tokens  ( 2%) │
│  Query do usuário + reformulação         ~200 tokens  (<1%) │
├─────────────────────────────────────────────────────────────┤
│  ✅ DISPONÍVEL PARA CHUNKS RECUPERADOS  119.800 tokens (93%)│
└─────────────────────────────────────────────────────────────┘
```

#### 3.2 Capacidade Teórica vs. Capacidade Recomendada

| Métrica | Valor |
|---------|-------|
| Espaço disponível para chunks | ~120.000 tokens |
| Chunks de 500 tokens — capacidade máxima teórica | **240 chunks** |
| Chunks recomendados (40% da janela disponível)¹ | **~97 chunks** |
| Chunks recomendados com margem de segurança | **20–30 chunks** |

> ¹ Justificativa: o efeito *lost in the middle* torna irracional usar 100% da janela disponível.

#### 3.3 O Efeito Lost in the Middle e sua Implicação Prática

Estudos de atenção em LLMs demonstram que o modelo presta atenção desproporcional ao **início** e ao **fim** do contexto. Informações posicionadas no meio de contextos longos têm taxa de recuperação até 50% menor.

**Consequência direta para este projeto:**

```
Contexto com 200 chunks enviados ao modelo:

  [chunks 1-5]   ← Alta atenção ✅
  [chunks 6-195] ← Atenção degradada ⚠️  (a resposta provavelmente está aqui)
  [chunks 196-200] ← Alta atenção ✅
```

Enviar 240 chunks (máximo teórico) **não melhora** a qualidade — degrada. O chunk correto provavelmente ficará sepultado no meio.

**Recomendação operacional:** usar no máximo **20 chunks por query**, priorizando os de maior score de relevância, e posicioná-los no início do contexto, imediatamente após o system prompt.

---

### 4. Estratégia de Chunking Recomendada

#### 4.1 Princípio Geral

A estratégia de chunking não deve ser definida pelo tipo de documento — deve ser definida pelo **tipo de pergunta que o usuário vai fazer**.

Os atendentes da NovaTech fazem três classes de perguntas:

| Classe | Exemplo | Natureza |
|--------|---------|---------|
| **Lookup pontual** | "Qual o prazo para cliente Tier 3 na região Norte?" | Busca de valor específico em tabela |
| **Procedimento** | "Quais são os passos para registrar uma reclamação de avaria?" | Sequência de etapas — contexto contínuo |
| **Política/regra** | "A NovaTech aceita devolução de carga perigosa?" | Interpretação de texto normativo |

Cada classe exige uma estratégia diferente.

---

#### 4.2 Chunking por Tipo de Conteúdo

**A) Tabelas de Dados → Chunking por Linha (micro-chunks: ~50–150 tokens)**

```
Cada linha da tabela = 1 chunk
Com todos os cabeçalhos explicitados inline

Exemplo:
[DOC: tabela_frete_v6.pdf | pág.4 | TABELA: Frete Regional]
Região: Sul | Cliente: Tier_2 | Modalidade: Expresso | Prazo: 24h | Valor: R$78 | Peso_máx: 30kg
```

**Justificativa:** perguntas de lookup exigem precisão atômica. Um chunk grande com 50 linhas de tabela vai ter o valor correto enterrado no meio — efeito *lost in the middle* dentro do próprio chunk.

---

**B) Procedimentos e Fluxos → Chunking por Seção Semântica (chunks: ~300–500 tokens)**

```
Delimitadores: H2/H3 + número de passos
Preservar a sequência completa de um procedimento em um único chunk
Não quebrar um fluxo no meio de um passo

Exemplo de chunk:
[DOC: manual_reclamacoes_v3.pdf | seção: 4.2 Registro de Avaria]
"Para registrar uma ocorrência de avaria em carga: 
 1. Acionar o cliente via CRM (protocolo obrigatório) 
 2. Solicitar fotos da avaria em até 2h 
 3. Abrir ticket no sistema Omega com tag [AVARIA] 
 4. Encaminhar para equipe de sinistros em até 4h úteis"
```

**Justificativa:** procedimentos são unidades semânticas indivisíveis. Quebrar um fluxo de 8 etapas em dois chunks de 4 força o modelo a inferir a continuidade — e ele frequentemente erra.

---

**C) Políticas e Normas → Chunking com Overlap (chunks: ~400–600 tokens, overlap: 20%)**

```
Overlap de ~100 tokens entre chunks consecutivos
Preservar o parágrafo que define o escopo antes da regra

Exemplo:
Chunk N:   "...conforme Resolução ANTT 5.820/2020. Para cargas de classe 3 
            (inflamáveis), a NovaTech não aceita devolução após..."
Chunk N+1: "...não aceita devolução após o início do transporte. Exceções 
            aplicam-se somente quando comprovado defeito de embalagem..."
```

**Justificativa:** políticas frequentemente têm exceções que modificam a regra principal. Sem overlap, o chunk da regra e o chunk da exceção ficam separados — o modelo responde pela regra sem conhecer a exceção.

---

#### 4.3 Quadro-Resumo da Estratégia

| Tipo de conteúdo | Estratégia | Tamanho alvo | Overlap | Chunks/query |
|-----------------|-----------|-------------|---------|-------------|
| Linhas de tabela (frete, SLA) | Por linha + cabeçalhos inline | 50–150 tokens | 0% | 10–15 |
| Procedimentos (passo-a-passo) | Por seção semântica (H2/H3) | 300–500 tokens | 5% | 5–10 |
| Políticas e normas | Parágrafo com overlap | 400–600 tokens | 20% | 5–8 |
| Páginas wiki (mistas) | Por header + resolução de links | 300–500 tokens | 10% | 5–10 |
| **Total máximo por query** | | | | **≤ 20 chunks** |

---

#### 4.4 Estratégia de Retrieval Complementar ao Chunking

O chunking sozinho não resolve o problema de qualidade. As seguintes técnicas devem acompanhar:

1. **Hybrid Search (BM25 + vetorial):** perguntas com termos exatos ("frete Tier 2") se beneficiam de BM25; perguntas semânticas ("como funciona a devolução") exigem similaridade vetorial. Azure AI Search suporta ambos nativamente.
2. **Re-ranking pós-retrieval (cross-encoder):** buscar 50 chunks candidatos com o índice vetorial, re-ranquear com um cross-encoder (ex.: `ms-marco-MiniLM`) e enviar apenas os 20 melhores ao LLM.
3. **Query expansion:** antes do retrieval, usar o próprio LLM para gerar 2–3 reformulações da pergunta do usuário, enriquecendo o recall sem ampliar o contexto final.
4. **Metadados para filtragem pré-retrieval:** usar filtros por `tipo_documento`, `area_responsavel` e `data_versao` para restringir o espaço de busca antes da comparação vetorial.

---

### 5. Riscos Críticos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|-------------|---------|-----------|
| Documentos contraditórios entre versões | Alta (confirmado pela NovaTech) | Alto | Incluir `data_versao` nos metadados; quando dois chunks conflitantes forem recuperados, o prompt deve instruir o modelo a indicar o conflito e citar a versão mais recente |
| OCR com baixa qualidade em docs escaneados | Média | Alto | Threshold de confiança mínimo; fila de revisão humana para docs abaixo do limiar |
| Planilhas com valores desatualizados (lag de reprocessamento) | Média | Alto | Pipeline de ingestão automatizado com trigger mensal + alerta se falhar |
| Drift semântico por macros/HTML não tratados (Confluence) | Média | Médio | Validação do pipeline com sample de 50 páginas antes do go-live |
| Alucinação em perguntas fora do escopo | Baixa-Média | Alto | Instrução explícita no system prompt: "Se a informação não estiver nos documentos recuperados, responda 'Não encontrei essa informação na documentação oficial' e indique ao atendente buscar com o gestor responsável." |

---

### 6. Impacto Operacional Esperado

| Métrica | Hoje | Com Assistente | Variação |
|---------|------|---------------|---------|
| Tempo médio de busca/chamado | 12 min | < 2 min | **−83%** |
| Chamados com consulta documental/dia | 192 (60% de 320) | 192 | — |
| Horas gastas em busca/dia | 38,4 h | 6,4 h | **−32 h/dia** |
| Equivalente FTE liberado | — | — | **~4 FTEs** |
| Consistência das respostas | Variável ("quem sabe") | Baseada em fonte oficial | Alta |

> As 32 horas/dia liberadas podem ser redirecionadas para atendimento de maior complexidade, reduzindo o backlog sem aumento de headcount.

---

### 7. Próximos Passos Recomendados (Discovery — Mês 1)

1. **Auditoria de qualidade documental:** amostrar 50 PDFs, 50 páginas wiki e 5 planilhas para validar as estimativas de OCR, macros e fórmulas antes de dimensionar o pipeline de ingestão.
2. **Mapeamento de conflitos:** identificar os documentos contraditórios conhecidos e definir regra de precedência com as áreas de Operações, Compliance e Comercial.
3. **Definição do dicionário de domínio:** levantar termos técnicos logísticos para o spell-checker do OCR e para query expansion.
4. **Prova de conceito com 100 documentos:** validar pipeline de ingestão (extração → chunking → embedding → retrieval) com uma amostra representativa antes de escalar.
5. **Construção do golden dataset de avaliação:** coletar 50–100 pares (pergunta real de atendente, resposta correta com fonte) para medir precision@k e faithfulness do pipeline antes do go-live.

---

### Resumo Final (gerado ao final da conversa)

Com base nos dados fornecidos, os pontos-chave da análise são:

**Desafios por fonte:**
- PDFs com tabelas: extratores genéricos destroem a relação linha/coluna → serializar cada linha com cabeçalhos inline via `camelot`/`pdfplumber`.
- PDFs escaneados: OCR ruim distorce embeddings → Azure Document Intelligence com threshold de confiança ≥ 80%.
- Wiki Confluence: fragmentação por design + macros que geram ruído → export via API REST, strip de macros, resolução de links até 1 nível.
- Planilhas com fórmulas: o LLM não executa Excel → materializar valores calculados antes de indexar com `openpyxl` + `xlcalculator`.

**Tamanho da base:** ~4,2M tokens (33× a janela do GPT-4o). RAG é obrigatório.

**Orçamento de contexto:** dos 128K tokens disponíveis, recomenda-se no máximo **20 chunks por query** — enviar mais degrada a qualidade pelo efeito *lost in the middle*.

**Chunking:** micro-chunks por linha para lookups em tabelas; chunks por seção semântica para procedimentos; chunks com overlap de 20% para políticas com exceções.

---

*Documento gerado automaticamente como registro da interação. Projeto NovaTech × DB1 — Junho 2026.*
