# Sessão de Revisão Técnica — Pipeline RAG NovaTech
**Data:** Junho 2026  
**Tipo:** Análise crítica de documento técnico via IA  
**Documento base:** `novatech_rag_analise_tecnica.md` (DB1 × NovaTech, v1.0)

---

## Contexto

O usuário submeteu a análise técnica de um pipeline RAG para atendimento ao cliente da NovaTech e solicitou uma revisão crítica identificando pontos fracos, estimativas otimistas e riscos não considerados. O resultado foi entregue primeiro em formato de resposta conversacional e, em seguida, exportado como arquivo Markdown estruturado.

---

## Interação

---

### Turno 1

**Usuário:**
> Dado a analise técnica em anexo, identifique pontos fracos, estimativas otimistas demais ou riscos que você não foram considerados.

**Assistente:**

Após leitura completa do documento (`novatech_rag_analise_tecnica.md`), foram identificados os seguintes pontos:

---

#### Estimativas Otimistas Demais

**1. Volume de tokens — densidade de 300 palavras/página subestimada para PDFs técnicos**

O documento usa 300 palavras/página como estimativa "conservadora" para 800 documentos de PDFs técnicos com tabelas. PDFs de logística são densos: tabelas de frete com 15+ colunas, listas de SKUs e normativas costumam ultrapassar 500–700 palavras por página em conteúdo útil.

Se a densidade real for 500 palavras/página, o corpus sobe de 4,2M para ~7M de tokens — impacto direto no custo de embedding, tempo de ingestão e dimensionamento do Azure AI Search. A validação proposta nos próximos passos precisa incluir contagem real de tokens, não apenas estimativa.

**2. Redução de 83% no tempo de atendimento — sem baseline de validação**

A projeção de 12 min → 2 min é apresentada como fato, mas não há metodologia descrita para chegar ao número atual de 12 minutos. Não está claro se esse valor vem de medição sistemática, estimativa dos atendentes ou dado aproximado fornecido pela NovaTech.

Além disso, o modelo assume que todo o tempo de busca é eliminável pelo assistente. Na prática, parte dos 12 min inclui atividades que o RAG não substitui: discutir a situação com o cliente, interpretar nuances, escalar para um gestor. Uma redução de 50–60% seria mais defensável sem dados de time-motion reais.

**3. `xlcalculator` para materializar planilhas complexas — confiabilidade não estabelecida**

A estratégia para planilhas com fórmulas interdependentes depende de `xlcalculator`. Essa biblioteca tem cobertura parcial das funções do Excel — especialmente `VLOOKUP`, funções de data, fórmulas matriciais e referências entre abas são fontes conhecidas de falha silenciosa. O documento não menciona estratégia de validação dos valores materializados. Uma planilha de cálculo de frete com erros silenciosos nos valores indexados é pior do que não indexá-la.

---

#### Pontos Fracos Técnicos

**1. Resolução de links do Confluence limitada a 1 nível — insuficiente para wikis reais**

A estratégia propõe seguir links internos "até 1 nível de profundidade". Em wikis corporativas de logística, políticas relevantes frequentemente estão 2–3 níveis abaixo da página raiz. Limitar a resolução a 1 nível deixa uma parcela significativa do conhecimento distribuído não consolidada nos chunks.

**2. Ausência de estratégia para perguntas multi-hop**

O quadro de classes de perguntas (seção 4.1) não menciona perguntas que cruzam múltiplas fontes heterogêneas, por exemplo: *"Para o cliente Transportes Silva, Tier 2 na região Sul, qual o prazo e valor do frete expresso para Manaus considerando a promoção vigente no mês?"* — que exige cruzar tabela de frete (PDF), tabela de clientes (planilha), exceções regionais (wiki) e tabela de promoções (outra planilha). O pipeline não tem mecanismo explícito para compor chunks de fontes distintas em uma resposta coerente.

**3. Re-ranking com cross-encoder não dimensionado para latência**

A recomendação de buscar 50 chunks e re-ranquear com `ms-marco-MiniLM` não menciona impacto de latência. Um cross-encoder rodando na CPU sobre 50 pares pode adicionar 300–800ms. Para respostas em menos de 10–15 segundos — expectativa razoável de atendentes em chamada ativa — esse passo precisa ser benchmarked explicitamente.

**4. Detecção de conflito entre documentos depende de coincidência no retrieval**

A mitigação para documentos contraditórios assume que ambos os chunks conflitantes apareçam na mesma query. Se o retrieval retornar apenas o chunk da versão desatualizada, o modelo responderá com confiança usando o dado errado. A mitigação real requer deduplicação e marcação de versões na ingestão, não apenas no retrieval.

**5. Sem estratégia para atualizações incrementais**

A ingestão é tratada como evento mensal. Não há menção a como lidar com atualizações parciais: um PDF revisado, uma página wiki editada, uma linha de tabela de frete alterada fora do ciclo. Re-ingerir todo o corpus mensalmente tem custo e janela de inconsistência elevados. Um pipeline de delta ingestion está ausente da proposta.

---

#### Riscos Não Considerados

**1. Automation bias dos atendentes**

O documento foca inteiramente na qualidade técnica das respostas, mas não menciona o risco comportamental de atendentes tratarem as respostas do assistente como verdade absoluta. Em logística, uma resposta incorreta sobre prazo ou valor de frete pode gerar comprometimento contratual antes que o erro seja detectado. Não há mecanismo de interface (ex.: sempre exibir a fonte, exigir confirmação antes de comunicar ao cliente) que mitigue esse risco.

**2. Documentos sem `data_versao` identificável**

A estratégia de resolução de conflitos depende do campo `data_versao`. PDFs escaneados ou exportações antigas da wiki frequentemente não têm data identificável ou têm datas inconsistentes (data de escaneamento ≠ data de criação). Sem curadoria de metadados, uma parcela dos documentos entra no índice sem `data_versao` confiável.

**3. Dados sensíveis indexados sem controle de acesso**

Wikis e planilhas corporativas frequentemente contêm dados que não devem ser acessíveis a todos os atendentes: valores de contratos, dados pessoais de clientes, margens comerciais, documentos de RH incluídos por engano no Confluence. O documento não propõe nenhuma camada de controle de acesso ou sanitização antes da indexação.

**4. Latência adicional da query expansion**

A técnica de query expansion propõe uma chamada adicional ao LLM antes de cada busca — potencialmente dobrando a latência percebida pelo atendente. Em atendimento telefônico com o cliente na linha aguardando, esse custo precisa ser avaliado frente ao ganho de recall.

**5. Sem monitoramento contínuo pós go-live**

O golden dataset proposto na seção 7 cobre apenas a avaliação pré go-live. Não há proposta de monitoramento contínuo pós-produção: sem loop de feedback (atendentes marcando respostas incorretas, métricas de "não encontrei informação", reamostragem periódica do golden dataset), a qualidade pode degradar silenciosamente conforme documentos são atualizados.

---

**Tabela resumo:**

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

### Turno 2

**Usuário:**
> gere no formato markdown

**Assistente:**

Gerou o arquivo `novatech_rag_analise_critica.md` com a análise estruturada em cinco seções:

1. Estimativas Otimistas Demais (3 itens)
2. Pontos Fracos Técnicos (5 itens)
3. Riscos Não Considerados (5 itens)
4. Tabela resumo com severidade
5. Recomendações Prioritárias (6 itens)

---

### Turno 3

**Usuário:**
> gere um markdown com essa interação

**Assistente:**

Gerou o presente arquivo `novatech_rag_sessao_revisao.md` documentando a sessão completa.

---

## Arquivos Gerados

| Arquivo | Descrição |
|---------|-----------|
| `novatech_rag_analise_critica.md` | Análise crítica estruturada do documento técnico |
| `novatech_rag_sessao_revisao.md` | Registro desta sessão de revisão (este arquivo) |

---

*Sessão registrada para fins de rastreabilidade e documentação do processo de revisão técnica.*
