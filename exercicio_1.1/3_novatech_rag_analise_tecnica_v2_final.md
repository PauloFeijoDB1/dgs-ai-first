# Análise Técnica — Pipeline RAG para NovaTech
**Projeto:** Assistente de IA para Atendimento ao Cliente
**Cliente:** NovaTech · **Contratada:** DB1
**Data:** Junho 2026 · **Versão:** 2.0 *(revisada com análise crítica interna)*

---

## Sumário Executivo

A NovaTech possui entre **4,2 e 7 milhões de tokens** de documentação distribuídos entre PDFs técnicos, wiki Confluence e planilhas — o que torna inviável qualquer abordagem de contexto estático. Um pipeline RAG bem calibrado é a única estratégia viável para o cenário de atendimento.

Esta versão incorpora os resultados de uma análise crítica interna da v1.0, corrigindo estimativas otimistas, adicionando estratégias ausentes e explicitando riscos operacionais que a versão anterior não contemplava. As principais atualizações são: revisão do volume estimado de tokens, adição de estratégia para perguntas multi-hop, detalhamento de controle de acesso, inclusão de delta ingestion, benchmark de latência end-to-end e monitoramento contínuo pós go-live.

> **Nota sobre a projeção de impacto operacional:** a redução estimada de 83% no tempo de busca (12 min → 2 min) é baseada em dados fornecidos pela NovaTech e não foi validada por medição sistemática de time-motion. A seção 6 apresenta os números com essa ressalva e propõe uma metodologia de validação.

---

## 1. Análise por Tipo de Fonte

### 1.1 PDFs com Tabelas Complexas (tabelas de frete com 15+ colunas)

#### Desafio para o pipeline RAG

Extratores de PDF genéricos (PyMuPDF, pdfplumber) serializam tabelas como texto contínuo, destruindo a relação entre cabeçalho de coluna e valor de célula. Uma tabela com 15 colunas e 80 linhas vira um bloco de ~1.200 tokens onde a informação estrutural é perdida. O LLM recebe um chunk como:

```
Cliente_A Regional_SP Prazo_3d Frete_R$45 Seguro_1% ... [linha 2] Cliente_B ...
```

sem saber que `R$45` corresponde à coluna `Frete_Padrão` e não à coluna `Frete_Expresso`.

#### Impacto na qualidade das respostas

Respostas com valores trocados entre colunas adjacentes — o modelo confabula a relação linha/coluna. Perguntas como *"qual o prazo para cliente Tier 2 na região Sul com frete expresso?"* exigem intersecção de linha + coluna, que texto serializado ingênuo não preserva.

#### Estratégia de tratamento

1. **Extração estruturada:** usar `camelot` ou `pdfplumber` para detectar e extrair tabelas como DataFrames antes do chunking.
2. **Serialização semântica por linha:** cada linha da tabela vira um documento independente com todos os cabeçalhos explicitados:
   ```
   [TABELA: Frete por Região] Cliente_Tier: 2 | Região: Sul | Modalidade: Expresso | Prazo: 24h | Valor: R$78,00 | Seguro: 1,5%
   ```
3. **Metadados de proveniência:** nome do documento, número da página, nome da tabela — para citação de fonte na resposta.
4. **Fallback visual (tabelas escaneadas):** para tabelas embutidas como imagem, usar GPT-4o Vision ou Azure Document Intelligence para extração OCR + estrutura.

---

### 1.2 PDFs Escaneados (OCR necessário)

#### Desafio para o pipeline RAG

Documentos escaneados não possuem camada de texto. OCR nativo de qualidade baixa gera ruído léxico grave: `"prazo de entrega"` pode virar `"praz0 de entrcga"`. Isso degrada o embedding — o vetor semântico do chunk é distorcido — e o retrieval falha para queries que dependem exatamente dessas palavras.

#### Impacto na qualidade das respostas

Falsos negativos no retrieval: o chunk correto existe no índice mas não é recuperado porque sua representação vetorial foi corrompida pelo OCR. O atendente pergunta algo que está no documento e o assistente responde "não encontrei informações" — pior do que o cenário atual.

#### Estratégia de tratamento

1. **Pré-processamento com Azure Document Intelligence (Form Recognizer):** suportado pelas licenças E3 + Azure AI Services já provisionados pela NovaTech. Extrai texto com confiança por palavra e sinaliza blocos de baixa confiança.
2. **Filtro de qualidade OCR:** rejeitar chunks com score médio de confiança < 80% e sinalizar o documento para revisão humana.
3. **Post-processing de normalização:** spell-checker com dicionário customizado do domínio logístico (termos como "RNTRC", "CTE", "ANTT") para corrigir erros sistemáticos de OCR.
4. **Identificação e catalogação:** manter lista de documentos escaneados na camada de metadados para priorizar reprocessamento quando forem digitalizados na origem.
5. **Curadoria de metadados de data:** PDFs escaneados frequentemente não possuem data de criação confiável (a data registrada pode ser a de escaneamento, não a do documento original). Incluir etapa de curadoria manual para atribuição de `data_versao` a documentos sem metadado confiável — sem isso, a lógica de resolução de conflitos por versão mais recente se torna inutilizável para essa classe de documentos.

---

### 1.3 Wiki Confluence com Links Internos e Macros

#### Desafio para o pipeline RAG

Páginas wiki são frequentemente **fragmentadas por design**: a resposta completa para uma pergunta está distribuída entre a página principal + 3 páginas linkadas. Chunks de uma única página ficam semanticamente incompletos. Macros customizadas do Confluence (expand, panel, jira-issues) geram lixo HTML no export e precisam ser removidas antes do embedding. Links internos do tipo `[ver política de devolução|/wiki/x/123]` perdem significado fora do contexto da wiki.

Em wikis corporativas de logística, é comum que políticas relevantes estejam 2–3 níveis abaixo da página raiz — por exemplo: "Atendimento" → "Procedimentos de Devolução" → "Política de Carga Perigosa" → "Exceções ANTT". Limitar a resolução de links a 1 nível deixa uma parcela significativa do conhecimento distribuído não consolidada nos chunks.

#### Impacto na qualidade das respostas

O modelo recebe um chunk que diz *"conforme descrito na política de devolução (ver link)"* sem ter acesso ao conteúdo da página linkada — resposta incompleta ou evasiva. Macros não tratadas inserem tokens de ruído que diluem o sinal semântico do embedding.

#### Estratégia de tratamento

1. **Export via API REST do Confluence** (não export HTML manual): usar a API v2 para extrair conteúdo em formato storage (XML estruturado) e converter para Markdown limpo com `atlassian-python-api` + `markdownify`.
2. **Resolução de links internos até 3 níveis de profundidade:** no momento do processamento, seguir links internos recursivamente (máx. 3 níveis) e incluir um resumo da página linkada como contexto no chunk pai (inline context injection). A profundidade máxima deve ser validada durante a auditoria de qualidade documental — para wikis mais rasas, 2 níveis pode ser suficiente.
3. **Strip de macros:** regex + parser XML para remover macros antes da indexação, preservando apenas o texto visível.
4. **Chunking por seção semântica:** usar os headers H1/H2/H3 como delimitadores naturais de chunk — respeita a estrutura editorial da wiki.

---

### 1.4 Planilhas com Fórmulas Interdependentes

#### Desafio para o pipeline RAG

Planilhas não são documentos de texto — são **modelos de cálculo**. Uma planilha de cálculo de frete pode ter a célula `F15 = B15 * VLOOKUP(C15, TabelaZonas, 3, FALSE) * (1 + TaxaSeguro)`. O valor final só existe em tempo de execução; o texto extraído é `=B15*VLOOKUP(...)`, não `R$145,00`. Além disso, dependências entre abas criam contexto invisível: a resposta correta para *"quanto custa frete para Manaus?"* pode depender de valores em 3 abas diferentes.

#### Impacto na qualidade das respostas

O LLM não executa fórmulas. Se o pipeline indexar fórmulas como texto, o modelo vai tentar interpretar a sintaxe do Excel como linguagem natural e produzir respostas incorretas ou inventadas.

#### Estratégia de tratamento

1. **Execução e materialização dos valores antes da indexação:** usar `openpyxl` para leitura estrutural e `xlcalculator` para materializar fórmulas Python-side. **Atenção:** `xlcalculator` tem cobertura parcial das funções do Excel — funções como `VLOOKUP`, referências entre abas, fórmulas matriciais e funções de data são fontes conhecidas de falha silenciosa. Antes de adotar como solução de produção, é obrigatório validar o output contra uma amostra representativa das planilhas mais complexas, comparando os valores calculados com os produzidos pelo Excel ou LibreOffice. Uma planilha com erros silenciosos nos valores indexados é pior do que não indexá-la. Alternativa mais robusta: exportar para CSV via Excel automation (COM automation no Windows ou LibreOffice headless no Linux) para garantir fidelidade total dos valores calculados.
2. **Indexar valores + contexto de rótulo:**
   ```
   [PLANILHA: Tabela_Frete_2025-06] Origem: SP | Destino: AM | Peso: até 10kg | Modalidade: Rodoviário | Valor: R$ 312,00
   ```
3. **Snapshot versionado com delta ingestion:** como as planilhas são atualizadas mensalmente, implementar pipeline automatizado de reprocessamento. Manter versão atual + 1 versão anterior para auditoria. Importante: o pipeline deve suportar reprocessamento incremental (apenas a planilha alterada), não apenas reprocessamento total do corpus — ver seção 5 sobre delta ingestion.
4. **Documentar dependências entre abas:** mapear as dependências para garantir que o snapshot capture o estado completo e consistente de cada planilha.

---

## 2. Estimativa do Tamanho da Base em Tokens

A estimativa original usava 300 palavras/página como densidade "conservadora" para PDFs técnicos. PDFs de logística com tabelas de frete de 15+ colunas, listas de SKUs e normativas com anexos tabulares costumam ter densidade de 500–700 palavras por página em conteúdo útil. O intervalo abaixo reflete os dois cenários:

| Fonte | Qtd. | Cenário Base (300 pal/pág.) | Cenário Denso (500 pal/pág.) |
|-------|------|--------------------------|---------------------------|
| PDFs (800 docs × 10 pág.) | 8.000 páginas | **3,2 M tokens** | **5,3 M tokens** |
| Wiki Confluence (400 páginas) | 400 páginas | **800 K tokens** | **800 K tokens** |
| Planilhas (50 × 5 abas × ~200 células úteis) | 50 planilhas | **200 K tokens** | **200 K tokens** |
| **TOTAL** | | **~4,2 M tokens** | **~6,3 M tokens** |

> A densidade real será aferida na auditoria de qualidade documental (passo 1 dos próximos passos), com **contagem real de tokens** em uma amostra de 50 PDFs — não apenas estimativa por densidade média. O dimensionamento do Azure AI Search e o orçamento de embedding devem ser revisados após essa auditoria.

### Interpretação

- No cenário denso, o corpus pode ser até **50% maior** do que a estimativa original — impacto direto no custo de embedding, no tempo de ingestão e no storage do índice vetorial.
- Em ambos os cenários, o corpus é entre 33 e 49 vezes a janela de 128K do GPT-4o. RAG com retrieval seletivo é obrigatório, não opcional.
- O índice vetorial (embeddings + metadados) ocupará entre **630 MB e ~950 MB** a 1.536 dimensões float32 (padrão `text-embedding-3-large`), bem dentro da capacidade do Azure AI Search.

---

## 3. Análise do Orçamento de Contexto

### 3.1 Partição da Janela (GPT-4o, 128K tokens)

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

### 3.2 Capacidade Teórica vs. Capacidade Recomendada

| Métrica | Valor |
|---------|-------|
| Espaço disponível para chunks | ~120.000 tokens |
| Tamanho médio de chunk (mix de tipos) | ~300 tokens |
| Chunks que cabem teoricamente | ~400 chunks |
| **Chunks recomendados por query** | **≤ 20 chunks** |
| Margem de segurança | ~94% da capacidade teórica não utilizada |

A recomendação de 20 chunks (6.000 tokens) — bem abaixo do limite técnico — é intencional: janelas grandes degradam a qualidade da atenção do LLM. O efeito *lost in the middle* é documentado: informação no meio de um contexto muito longo é sistematicamente ignorada pelo modelo.

---

## 4. Estratégia de Chunking

### 4.1 Classes de Perguntas dos Atendentes

Os atendentes da NovaTech fazem perguntas que se enquadram em quatro classes — a quarta (multi-hop) é crítica para o cenário de atendimento e exige tratamento específico:

| Classe | Exemplo | Natureza |
|--------|---------|---------|
| **Lookup pontual** | "Qual o prazo para cliente Tier 3 na região Norte?" | Busca de valor específico em tabela |
| **Procedimento** | "Quais são os passos para registrar uma reclamação de avaria?" | Sequência de etapas — contexto contínuo |
| **Política/regra** | "A NovaTech aceita devolução de carga perigosa?" | Interpretação de texto normativo |
| **Multi-hop** | "Para o cliente Transportes Silva (Tier 2, região Sul), qual o valor do frete expresso para Manaus com a promoção de junho?" | Cruzamento de múltiplas fontes heterogêneas |

Cada classe exige uma estratégia diferente. Perguntas multi-hop — que exigem combinar a tabela de frete (PDF), a tabela de clientes (planilha), as exceções regionais (wiki) e a tabela de promoções (outra planilha) — são frequentes no atendimento logístico e o pipeline precisa de um mecanismo explícito para compor chunks de fontes distintas em uma resposta coerente.

---

### 4.2 Chunking por Tipo de Conteúdo

#### A) Tabelas de Dados → Chunking por Linha (micro-chunks: ~50–150 tokens)

```
Cada linha da tabela = 1 chunk
Com todos os cabeçalhos explicitados inline

Exemplo:
[DOC: tabela_frete_v6.pdf | pág.4 | TABELA: Frete Regional]
Região: Sul | Cliente: Tier_2 | Modalidade: Expresso | Prazo: 24h | Valor: R$78 | Peso_máx: 30kg
```

**Justificativa:** perguntas de lookup exigem precisão atômica. Um chunk grande com 50 linhas de tabela vai ter o valor correto enterrado no meio — efeito *lost in the middle* dentro do próprio chunk.

---

#### B) Procedimentos e Fluxos → Chunking por Seção Semântica (chunks: ~300–500 tokens)

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

#### C) Políticas e Normas → Chunking com Overlap (chunks: ~400–600 tokens, overlap: 20%)

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

### 4.3 Quadro-Resumo da Estratégia

| Tipo de conteúdo | Estratégia | Tamanho alvo | Overlap | Chunks/query |
|-----------------|-----------|-------------|---------|-------------|
| Linhas de tabela (frete, SLA) | Por linha + cabeçalhos inline | 50–150 tokens | 0% | 10–15 |
| Procedimentos (passo-a-passo) | Por seção semântica (H2/H3) | 300–500 tokens | 5% | 5–10 |
| Políticas e normas | Parágrafo com overlap | 400–600 tokens | 20% | 5–8 |
| Páginas wiki (mistas) | Por header + resolução de links | 300–500 tokens | 10% | 5–10 |
| **Total máximo por query** | | | | **≤ 20 chunks** |

---

### 4.4 Estratégia de Retrieval Complementar ao Chunking

O chunking sozinho não resolve o problema de qualidade. As seguintes técnicas devem acompanhar:

1. **Hybrid Search (BM25 + vetorial):** perguntas com termos exatos ("frete Tier 2") se beneficiam de BM25; perguntas semânticas ("como funciona a devolução") exigem similaridade vetorial. Azure AI Search suporta ambos nativamente.

2. **Re-ranking pós-retrieval (cross-encoder):** buscar 50 chunks candidatos com o índice vetorial, re-ranquear com um cross-encoder (ex.: `ms-marco-MiniLM`) e enviar apenas os 20 melhores ao LLM. **Atenção de latência:** um cross-encoder rodando em CPU sobre 50 pares (query, chunk) pode adicionar 300–800ms à latência total. Esse passo deve ser benchmarked explicitamente durante a prova de conceito — se a meta for resposta em menos de 8–10 segundos (expectativa razoável para atendentes em chamada ativa), a viabilidade do re-ranking precisa ser validada com GPU ou com redução do pool de candidatos.

3. **Query expansion:** antes do retrieval, usar o próprio LLM para gerar 2–3 reformulações da pergunta do usuário, enriquecendo o recall sem ampliar o contexto final. **Atenção de latência:** query expansion implica uma chamada adicional à API do LLM antes de cada busca — potencialmente adicionando 1–2 segundos à latência percebida. Em contexto de atendimento telefônico, onde o cliente está na linha aguardando, esse custo precisa ser avaliado frente ao ganho de recall. Recomenda-se medir o ganho de recall com e sem query expansion na prova de conceito para decidir se o trade-off justifica o uso.

4. **Composição multi-hop:** para perguntas que exigem cruzamento de múltiplas fontes (ver seção 4.1), implementar um mecanismo de retrieval iterativo: a primeira busca recupera chunks de uma fonte, o modelo identifica quais informações complementares são necessárias, e uma segunda busca (com query derivada) recupera os chunks das fontes restantes. Isso pode ser implementado como um agente simples com 2–3 rounds de retrieval antes da geração da resposta final.

5. **Metadados para filtragem pré-retrieval:** usar filtros por `tipo_documento`, `area_responsavel` e `data_versao` para restringir o espaço de busca antes da comparação vetorial.

---

## 5. Arquitetura de Ingestão

### 5.1 Delta Ingestion (atualização incremental)

A v1.0 tratava a ingestão como evento único com trigger mensal. Na prática, documentos são atualizados de forma assíncrona: um PDF pode ser revisado, uma página wiki editada ou uma linha de tabela de frete alterada fora do ciclo mensal. Re-ingerir todo o corpus mensalmente tem custo elevado e cria uma janela de inconsistência de até 30 dias.

O pipeline deve suportar delta ingestion desde o início:

- **PDFs:** detectar novos arquivos e arquivos modificados por hash (MD5/SHA256) e timestamp. Re-indexar apenas os documentos alterados.
- **Confluence:** usar a API de histórico de revisões para detectar páginas modificadas desde a última ingestão. Re-processar apenas as páginas com revisão mais recente.
- **Planilhas:** detectar modificações por data de modificação do arquivo. Re-materializar e re-indexar apenas as planilhas alteradas.
- **Gerenciamento de chunks obsoletos:** ao re-indexar um documento, deletar todos os chunks anteriores desse documento (identificados pelo metadado `doc_id`) antes de inserir os novos — evita duplicatas e conflitos entre versões do mesmo documento.

### 5.2 Controle de Versão e Resolução de Conflitos

Documentos contraditórios entre versões são um risco confirmado pela NovaTech. A estratégia de resolução depende do campo `data_versao` nos metadados, o que exige dois pré-requisitos:

1. **Metadados confiáveis:** nem todos os documentos terão `data_versao` identificável automaticamente (especialmente PDFs escaneados e exportações antigas da wiki). O processo de curadoria de metadados deve ser explícito — documentos sem data confiável devem ser sinalizados e tratados manualmente antes da indexação.

2. **Detecção ativa de conflito na ingestão:** a mitigação de "quando dois chunks conflitantes forem recuperados, o prompt instrui o modelo a indicar o conflito" só funciona se ambos os chunks aparecerem na mesma query — o que não é garantido. A mitigação robusta exige um processo ativo no momento da ingestão: ao inserir um novo chunk, comparar com chunks existentes do mesmo `tipo_documento` + `area_responsavel` e sinalizar possíveis conflitos para revisão humana antes de disponibilizar no índice de produção.

### 5.3 Controle de Acesso por Perfil

Wikis e planilhas corporativas frequentemente contêm informações que não devem ser acessíveis a todos os atendentes: valores de contratos específicos, dados pessoais de clientes, margens comerciais, ou documentos de RH incluídos por engano no Confluence.

**Antes de definir o escopo de documentos a indexar**, as áreas de Operações, Compliance e Comercial devem mapear quais documentos cada perfil de atendente pode consultar. O pipeline de ingestão deve implementar:

- Metadado `perfil_acesso` em cada chunk (ex.: `atendimento_geral`, `atendimento_comercial`, `gestor`)
- Filtro pré-retrieval por `perfil_acesso` aplicado antes da comparação vetorial
- Auditoria periódica dos documentos indexados para identificar conteúdo sensível incluído inadvertidamente

---

## 6. Riscos Críticos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|-------------|---------|-----------|
| Documentos contraditórios entre versões | Alta (confirmado) | Alto | `data_versao` nos metadados + detecção ativa de conflito na ingestão (não apenas no retrieval) |
| OCR com baixa qualidade em docs escaneados | Média | Alto | Threshold de confiança ≥ 80%; fila de revisão humana; curadoria manual de `data_versao` |
| Planilhas com valores desatualizados | Média | Alto | Delta ingestion com trigger por modificação de arquivo + alerta se falhar |
| Drift semântico por macros/HTML não tratados | Média | Médio | Validação do pipeline com amostra de 50 páginas antes do go-live |
| Alucinação em perguntas fora do escopo | Baixa-Média | Alto | System prompt explícito: "Se a informação não estiver nos documentos recuperados, responda 'Não encontrei essa informação na documentação oficial'." |
| **Automation bias dos atendentes** | **Alta** | **Alto** | Interface sempre exibe a fonte do chunk recuperado; atendente deve confirmar a informação antes de comunicar ao cliente; treinamento explícito sobre limitações do assistente |
| Dados sensíveis indexados sem controle de acesso | Média | Alto | Mapeamento de perfis de acesso antes da ingestão; metadado `perfil_acesso` em cada chunk; filtro pré-retrieval |
| Documentos sem `data_versao` confiável | Média | Médio | Curadoria de metadados como etapa obrigatória do pipeline de ingestão |
| Latência acima do aceitável (query expansion + re-ranking) | Média | Médio | Benchmark de latência end-to-end como critério de aceite da PoC (meta: p95 < 8s) |
| Degradação silenciosa pós go-live | Média | Alto | Monitoramento contínuo com métricas de qualidade + loop de feedback dos atendentes |

---

## 7. Impacto Operacional Esperado

> **Aviso metodológico:** a redução de 83% no tempo de busca (12 min → 2 min) é baseada em estimativa fornecida pela NovaTech, sem medição sistemática de time-motion. O valor de 12 minutos não está documentado com metodologia clara — pode incluir atividades que o RAG não substitui (discutir a situação com o cliente, interpretar nuances, escalar para um gestor, aguardar confirmação). Uma redução de 50–60% seria uma projeção mais conservadora sem dados reais. Os números abaixo devem ser tratados como hipótese a validar, não como projeção garantida.

| Métrica | Hoje | Com Assistente (estimado) | Variação |
|---------|------|--------------------------|---------|
| Tempo médio de busca/chamado | 12 min* | < 2 min | **−83% (hipótese)** |
| Chamados com consulta documental/dia | 192 (60% de 320) | 192 | — |
| Horas gastas em busca/dia | 38,4 h | 6,4 h | **−32 h/dia** |
| Equivalente FTE liberado | — | — | **~4 FTEs** |
| Consistência das respostas | Variável ("quem sabe") | Baseada em fonte oficial | Alta |

*Valor fornecido pela NovaTech sem metodologia de medição documentada.*

**Ação recomendada:** incluir na auditoria documental (passo 1) uma medição de time-motion em uma amostra de 30–50 chamados reais, cronometrando o tempo gasto exclusivamente em busca documental. Isso vai calibrar a projeção de impacto antes do go-live.

---

## 8. Benchmark de Latência End-to-End

A latência percebida pelo atendente é a soma de todas as etapas do pipeline. O quadro abaixo estima a contribuição de cada componente e define a meta de aceite da prova de conceito:

| Etapa | Latência estimada | Observações |
|-------|-----------------|-------------|
| Query expansion (LLM call) | 1.000–2.000ms | Opcional; avaliar ganho de recall vs. custo |
| Embedding da query | 100–200ms | Azure OpenAI text-embedding-3-large |
| Retrieval híbrido (BM25 + vetorial) | 100–300ms | Azure AI Search |
| Re-ranking (cross-encoder, CPU) | 300–800ms | `ms-marco-MiniLM`; reduzir se exceder meta |
| Geração da resposta (GPT-4o, 20 chunks) | 2.000–5.000ms | Depende do tamanho do output |
| **Total estimado (p50)** | **3,6–8,3s** | |
| **Meta de aceite (p95)** | **< 8s** | Critério da prova de conceito |

Se o p95 exceder 8 segundos na PoC, as opções de otimização são: desabilitar query expansion, reduzir o pool de candidatos do re-ranking (50 → 20), usar GPU para o cross-encoder, ou substituir query expansion por HyDE (Hypothetical Document Embeddings).

---

## 9. Monitoramento Contínuo Pós Go-Live

A v1.0 propunha um golden dataset para avaliação pré go-live, mas não incluía monitoramento contínuo. Sem um loop de feedback, a qualidade do sistema pode degradar silenciosamente à medida que documentos são atualizados e o índice fica desatualizado.

O plano de monitoramento deve incluir:

1. **Métricas operacionais em tempo real:** taxa de respostas "não encontrei informação", tempo médio de resposta (p50/p95), volume de queries por tipo de documento recuperado.
2. **Feedback dos atendentes:** interface de marcação de respostas incorretas ou incompletas. Cada marcação gera um item para revisão no golden dataset.
3. **Reamostragem periódica do golden dataset:** a cada 30 dias, reavaliar o pipeline contra o golden dataset completo + os novos pares coletados pelo feedback dos atendentes. Queda de mais de 5 pontos percentuais em precision@5 ou faithfulness deve acionar uma revisão do pipeline.
4. **Alerta de delta ingestion:** monitorar falhas no pipeline de ingestão incremental. Documentos não reprocessados após atualização devem gerar alerta para a equipe técnica.
5. **SLA de qualidade:** definir, com as áreas de Operações e Compliance, o nível mínimo aceitável de acerto antes do go-live e o procedimento de rollback se as métricas caírem abaixo do SLA em produção.

---

## 10. Próximos Passos Recomendados (Discovery — Mês 1)

1. **Auditoria de qualidade documental com contagem real de tokens:** amostrar 50 PDFs, 50 páginas wiki e 5 planilhas. Incluir contagem real de tokens (não estimativa por densidade) para calibrar o volume do corpus e o dimensionamento do Azure AI Search.

2. **Validação do `xlcalculator`:** testar contra as planilhas mais complexas (especialmente as que usam `VLOOKUP`, referências entre abas e funções de data), comparando os valores calculados com os produzidos pelo Excel/LibreOffice. Decidir entre `xlcalculator` e exportação via LibreOffice headless com base nos resultados.

3. **Mapeamento de perfis de acesso:** com Operações, Compliance e Comercial, definir quais documentos cada perfil de atendente pode consultar — antes de definir o escopo de indexação.

4. **Mapeamento de conflitos documentais:** identificar os documentos contraditórios conhecidos e definir regra de precedência por área. Incluir avaliação de quais documentos não possuem `data_versao` confiável.

5. **Definição do dicionário de domínio:** levantar termos técnicos logísticos para o spell-checker do OCR e para query expansion.

6. **Prova de conceito com 100 documentos:** validar pipeline de ingestão (extração → chunking → embedding → retrieval) com amostra representativa. Incluir benchmark de latência end-to-end (meta: p95 < 8s) como critério de aceite.

7. **Construção do golden dataset de avaliação:** coletar 50–100 pares (pergunta real de atendente, resposta correta com fonte), com cobertura das quatro classes de perguntas — incluindo pelo menos 15–20 perguntas multi-hop. Usar para medir precision@k e faithfulness antes do go-live.

8. **Medição de time-motion:** cronometrar tempo de busca documental em 30–50 chamados reais para calibrar a projeção de impacto operacional com dados reais.

---

## Apêndice — Rastreabilidade das Alterações (v1.0 → v2.0)

| Seção | Alteração | Origem |
|-------|-----------|--------|
| Sumário Executivo | Intervalo de tokens (4,2 M → 4,2–7 M); aviso sobre baseline de 12 min | Análise crítica §1.1, §1.2 |
| Seção 1.2 (PDFs escaneados) | Adicionada curadoria de `data_versao` para docs escaneados | Análise crítica §3.2 |
| Seção 1.3 (Confluence) | Resolução de links ampliada de 1 para 3 níveis, com justificativa | Análise crítica §2.1 |
| Seção 1.4 (Planilhas) | Alerta sobre cobertura parcial do `xlcalculator`; alternativa via LibreOffice | Análise crítica §1.3 |
| Seção 2 (Tokens) | Tabela dual com cenário base e cenário denso | Análise crítica §1.1 |
| Seção 4.1 (Classes de perguntas) | Adicionada classe multi-hop | Análise crítica §2.2 |
| Seção 4.4 (Retrieval) | Avisos de latência para re-ranking e query expansion; estratégia multi-hop | Análise crítica §2.3, §3.4 |
| Seção 5 (Ingestão) | Delta ingestion, controle de versão ativo, controle de acesso por perfil | Análise crítica §2.5, §2.4, §3.3 |
| Seção 6 (Riscos) | Adicionados: automation bias, dados sensíveis, latência, degradação pós go-live | Análise crítica §3.1–§3.5 |
| Seção 7 (Impacto) | Aviso metodológico; ação de medição de time-motion | Análise crítica §1.2 |
| Seção 8 (Latência) | Seção nova: benchmark end-to-end e meta de aceite | Análise crítica §2.3, §3.4 |
| Seção 9 (Monitoramento) | Seção nova: monitoramento contínuo pós go-live | Análise crítica §3.5 |
| Próximos Passos | Adicionados: validação `xlcalculator`, mapeamento de acesso, time-motion, golden dataset multi-hop | Análise crítica §5 |

---

*Documento produzido para uso interno no projeto NovaTech × DB1. Esta versão incorpora a análise crítica interna de Junho 2026. Revisão técnica recomendada com as equipes de Operações, Compliance e Comercial da NovaTech antes da fase de desenvolvimento.*
