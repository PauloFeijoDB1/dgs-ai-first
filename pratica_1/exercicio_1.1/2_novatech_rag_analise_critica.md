# Análise Crítica — Pipeline RAG NovaTech
**Documento revisado:** Análise Técnica RAG para NovaTech v1.0 (Junho 2026)  
**Natureza desta revisão:** Identificação de pontos fracos, estimativas otimistas e riscos não considerados

---

## 1. Estimativas Otimistas Demais

### 1.1 Volume de tokens — densidade de 300 palavras/página subestimada para PDFs técnicos

O documento usa 300 palavras/página como estimativa "conservadora" para 800 documentos de PDFs técnicos com tabelas. Na prática, PDFs de logística são densos: tabelas de frete com 15+ colunas, listas de SKUs, normativas com parágrafos longos e anexos com dados tabulares costumam ultrapassar 500–700 palavras por página em conteúdo útil.

Se a densidade real for 500 palavras/página, o corpus sobe de 4,2M para **~7M de tokens** — impacto direto no custo de embedding, no tempo de ingestão e no dimensionamento do Azure AI Search. A validação proposta nos próximos passos (amostrar 50 PDFs) precisa incluir contagem real de tokens, não apenas estimativa.

### 1.2 Redução de 83% no tempo de atendimento — sem baseline de validação

A projeção de 12 min → 2 min é apresentada como fato, mas não há nenhuma metodologia descrita para chegar ao número atual de 12 minutos. Não está claro se esse valor vem de uma medição sistemática, de uma estimativa dos próprios atendentes ou de um dado aproximado fornecido pela NovaTech.

Além disso, o modelo assume que **todo o tempo de busca é eliminável pelo assistente**. Na prática, parte do tempo de 12 min inclui atividades que o RAG não substitui: discutir a situação com o cliente, interpretar nuances, escalar para um gestor, aguardar confirmação. Uma redução de 50–60% seria uma projeção mais defensável sem dados de time-motion reais.

### 1.3 `xlcalculator` para materializar planilhas complexas — confiabilidade não estabelecida

A estratégia para planilhas com fórmulas interdependentes depende de `xlcalculator` para executar fórmulas Python-side. Essa biblioteca tem cobertura parcial das funções do Excel — especialmente `VLOOKUP`, funções de data, fórmulas matriciais e referências entre abas são fontes conhecidas de falha silenciosa. O documento não menciona nenhuma estratégia de validação dos valores materializados (ex.: comparar output do `xlcalculator` com o Excel/LibreOffice em amostra representativa). Uma planilha de cálculo de frete com erros silenciosos nos valores indexados é pior do que não indexá-la.

---

## 2. Pontos Fracos Técnicos

### 2.1 Resolução de links do Confluence limitada a 1 nível — insuficiente para wikis reais

A estratégia propõe seguir links internos "até 1 nível de profundidade". Em wikis corporativas de logística, é comum que políticas relevantes estejam 2–3 níveis abaixo da página raiz (ex.: página de "Atendimento" → "Procedimentos de Devolução" → "Política de Carga Perigosa" → "Exceções ANTT"). Limitar a resolução a 1 nível deixa uma parcela significativa do conhecimento distribuído não consolidada nos chunks, especialmente para perguntas sobre políticas e regras.

### 2.2 Ausência de estratégia para perguntas multi-hop

O quadro de classes de perguntas (seção 4.1) cobre lookup pontual, procedimentos e políticas isoladas. Não há menção a perguntas que cruzam múltiplas fontes heterogêneas, por exemplo: *"Para o cliente Transportes Silva, que é Tier 2 na região Sul, qual o prazo e o valor do frete expresso para Manaus considerando a promoção vigente no mês?"* — que exige cruzar a tabela de frete (PDF), a tabela de clientes (planilha), as exceções regionais (wiki) e a tabela de promoções (outra planilha).

O pipeline como desenhado não tem mecanismo explícito para compor chunks de fontes distintas em uma resposta coerente. Isso é um gap real para o cenário de atendimento, onde perguntas compostas são frequentes.

### 2.3 Re-ranking com cross-encoder não dimensionado para latência

A seção 4.4 recomenda buscar 50 chunks candidatos e re-ranquear com um modelo cross-encoder (`ms-marco-MiniLM`). O documento não menciona o impacto de latência desse passo. Um cross-encoder rodando na CPU sobre 50 pares (query, chunk) pode adicionar 300–800ms à latência total. Para atingir a meta de resposta em menos de 2 minutos, isso pode não ser crítico — mas se o objetivo for respostas em menos de 10–15 segundos (expectativa razoável de atendentes em chamada ativa), esse passo precisa ser benchmarked explicitamente.

### 2.4 Detecção de conflito entre documentos depende de coincidência no retrieval

A mitigação para documentos contraditórios (identificada como risco de probabilidade "Alta") assume que "quando dois chunks conflitantes forem recuperados, o prompt instrui o modelo a indicar o conflito". Porém, isso só funciona se **ambos os chunks conflitantes aparecerem na mesma query**. Se o retrieval retornar apenas o chunk da versão desatualizada, o modelo não saberá que existe conflito — e vai responder com confiança usando o dado errado. A mitigação real requer um processo ativo de deduplicação e marcação de versões no momento da ingestão, não apenas no momento do retrieval.

### 2.5 Sem estratégia para atualizações incrementais

O documento trata a ingestão como um evento único ("pipeline de ingestão automatizado com trigger mensal"). Não há menção a como lidar com atualizações parciais: o que acontece quando um único PDF é revisado, uma página wiki é editada, ou uma linha de tabela de frete muda fora do ciclo mensal? Re-ingerir todo o corpus mensalmente tem custo e janela de inconsistência elevados. Um pipeline de delta ingestion (detectar apenas o que mudou e re-indexar somente esses chunks) é ausente da proposta.

---

## 3. Riscos Não Considerados

### 3.1 Risco de confiança excessiva do atendente ("automation bias")

O documento foca inteiramente na qualidade técnica das respostas, mas não menciona o risco comportamental de atendentes tratarem as respostas do assistente como verdade absoluta, sem verificação. Em logística, uma resposta incorreta sobre prazo ou valor de frete pode gerar comprometimento contratual com o cliente antes que o erro seja detectado. A proposta não inclui nenhum mecanismo de interface (ex.: sempre exibir a fonte, exigir confirmação do atendente antes de comunicar ao cliente) que mitigue esse risco operacional.

### 3.2 Risco de documentos sem data de versão identificável

A estratégia de resolução de conflitos depende do campo `data_versao` nos metadados. O documento não avalia o que acontece quando PDFs escaneados ou exportações antigas da wiki não têm data identificável ou têm datas inconsistentes (ex.: data de escaneamento ≠ data de criação do documento). Sem um processo de curadoria de metadados, uma parcela dos documentos pode entrar no índice sem `data_versao` confiável, tornando inutilizável a lógica de "preferir versão mais recente".

### 3.3 Risco de dados sensíveis indexados inadvertidamente

Wikis e planilhas corporativas frequentemente contêm dados que não devem ser acessíveis a todos os atendentes: valores de contratos específicos, dados pessoais de clientes, margens comerciais, ou documentos de RH incluídos por engano no Confluence. O documento não propõe nenhuma camada de controle de acesso ou sanitização de conteúdo antes da indexação. Um atendente de atendimento ao cliente não deveria ter acesso, via RAG, a um documento de política salarial indexado junto com os manuais operacionais.

### 3.4 Risco de latência de embedding no momento da consulta (query expansion)

A técnica de query expansion propõe usar o LLM para gerar 2–3 reformulações da pergunta antes do retrieval. Isso significa uma chamada adicional à API do LLM antes de cada busca — potencialmente dobrando a latência percebida pelo atendente. Em contexto de atendimento telefônico, onde o cliente está na linha aguardando, esse custo de latência é significativo e precisa ser explicitamente avaliado frente ao ganho de recall.

### 3.5 Risco de degradação silenciosa pós go-live

O documento propõe um golden dataset de avaliação para medir qualidade antes do go-live (seção 7). Não há, contudo, nenhuma proposta de monitoramento contínuo pós-produção. Sem um loop de feedback (ex.: atendentes marcando respostas incorretas, métricas de taxa de "não encontrei informação", detecção de drift por reamostragem periódica do golden dataset), a qualidade do sistema pode degradar silenciosamente à medida que documentos são atualizados e o índice fica desatualizado.

---

## 4. Resumo dos Pontos de Atenção

| Categoria | Item | Severidade |
|-----------|------|-----------|
| Estimativa otimista | Volume real de tokens pode ser até 70% maior | Alta |
| Estimativa otimista | Redução de 83% sem baseline validado | Média |
| Estimativa otimista | Confiabilidade do `xlcalculator` não verificada | Alta |
| Ponto fraco técnico | Links Confluence limitados a 1 nível | Média |
| Ponto fraco técnico | Sem estratégia para perguntas multi-hop | Alta |
| Ponto fraco técnico | Latência do cross-encoder não avaliada | Média |
| Ponto fraco técnico | Detecção de conflito depende de coincidência no retrieval | Alta |
| Ponto fraco técnico | Sem estratégia de delta ingestion | Média |
| Risco não considerado | Automation bias dos atendentes | Alta |
| Risco não considerado | Documentos sem `data_versao` confiável | Média |
| Risco não considerado | Dados sensíveis indexados sem controle de acesso | Alta |
| Risco não considerado | Latência adicional da query expansion | Média |
| Risco não considerado | Sem monitoramento contínuo pós go-live | Alta |

---

## 5. Recomendações Prioritárias

1. **Validar volume real de tokens** na auditoria de qualidade documental (passo 1 dos próximos passos), incluindo contagem real — não apenas estimativa por densidade média.
2. **Validar `xlcalculator`** contra uma amostra das planilhas mais complexas comparando com valores calculados pelo Excel/LibreOffice antes de adotar como solução de produção.
3. **Adicionar controle de acesso por perfil** antes de definir o escopo de documentos a indexar — o que cada papel de atendente pode consultar deve ser decidido antes da ingestão.
4. **Incluir benchmark de latência end-to-end** (query expansion + retrieval + re-ranking + geração) como critério de aceite da prova de conceito, com meta explícita (ex.: p95 < 8s).
5. **Projetar delta ingestion desde o início** para evitar reprocessamento total mensalmente e reduzir a janela de inconsistência.
6. **Definir estratégia de monitoramento pós go-live** com SLA de qualidade, mecanismo de feedback dos atendentes e reamostragem periódica do golden dataset.

---

*Revisão produzida como análise crítica interna. Recomenda-se discutir estes pontos com as equipes técnica e de operações antes da fase de desenvolvimento.*
