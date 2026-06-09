# Simulação de Atendimento — Assistente NovaTech
> **Base:** System Prompt v2.0 + Anexo B (Chunks de Referência RAG)
> **Data de geração:** 2024-12

---

## Pergunta 1 — Devolução de carga perigosa

**Atendente:** Qual o prazo de devolução para carga perigosa?

---

**Assistente NovaTech:**

**RESPOSTA DIRETA**
Cargas perigosas **não são elegíveis para devolução pelo processo padrão**. Não há prazo de devolução aplicável a essas cargas — o processo é diferente e requer tratamento individual.

**DETALHAMENTO**
As categorias de carga **não elegíveis** para devolução padrão incluem todas as classes 1 a 6 da ANTT (Resolução nº 5.947/2021):
- Classe 1: Explosivos
- Classe 2: Gases
- Classe 3: Líquidos inflamáveis
- Classe 4: Sólidos inflamáveis
- Classe 5: Oxidantes e peróxidos orgânicos
- Classe 6: Substâncias tóxicas e infectantes

O cliente deve ser encaminhado para o setor de **Gestão de Riscos** para tratamento individualizado.

**FONTES**
→ POL-001-B, seção 3.2: cargas perigosas classes 1–6 da ANTT não são elegíveis para devolução pelo processo padrão; encaminhar ao ramal 4500 (Gestão de Riscos).

**ALERTAS**
⚠ O FAQ-03 menciona que o setor de Riscos já autorizou exceções em casos anteriores, mas essa informação **não substitui a política formal**. Para o atendimento, use apenas a POL-001-B como referência. Se houver pedido de exceção, encaminhe ao **ramal 4500**.

---

**Análise:** Resposta correta. O assistente usou a POL-001-B (documento formal, prioridade 2 na hierarquia da Regra 5) e citou o FAQ-03 apenas como alerta, sinalizando que não substitui a política — conforme determina a Regra 5. Nenhum prazo foi inventado (Regra 2) e o canal de escalonamento foi indicado.

---

## Pergunta 2 — SLA de cliente Gold

**Atendente:** Meu cliente é Gold, qual o SLA de resolução?

---

**Assistente NovaTech:**

**INFORMAÇÃO NECESSÁRIA**

Este chamado é um **incidente crítico** ou um **chamado geral**?

**Por que preciso dessa informação:**
O SLA de resolução para clientes Gold varia conforme o tipo do chamado — chamados gerais têm resolução em até 24h úteis, enquanto incidentes críticos têm resolução em até 4h. Aplicar o prazo errado pode gerar expectativa incorreta para o cliente.

---

**Análise:** Resposta correta. O assistente aplicou a Regra 6 (solicitar contexto faltante antes de responder): o campo `tipo_chamado` não estava disponível no contexto da Seção 5, e a pergunta envolve SLA — exatamente uma das situações previstas na tabela da Regra 6. O assistente não forneceu os dois valores condicionalmente, pois a diferença entre os cenários (4h vs 24h) tem alto impacto operacional.

**Resposta esperada após esclarecimento (ex.: "chamado geral"):**

> Resolução em até **24h úteis**, com resposta inicial em até **2h úteis**.
> *(Fonte: SLA-2024-B, seção 2 — SLAs para chamados gerais, tier Gold)*

---

## Pergunta 3 — Frete especial para Manaus

**Atendente:** Quanto custa o frete para 600kg para Manaus?

---

**Assistente NovaTech:**

**INFORMAÇÃO NECESSÁRIA**

Qual é a **data de abertura** deste chamado?

**Por que preciso dessa informação:**
Existem duas versões da tabela de multiplicadores regionais para frete especial (PROC-042 v1 e PROC-042-v2). A versão aplicável depende da data de abertura do chamado — chamados anteriores a 01/12/2023 ainda em processamento usam a v1; chamados a partir de 01/12/2023 usam a v2. Os multiplicadores para a região Norte são diferentes entre as versões (1.6 vs 1.8), o que impacta diretamente o valor calculado.

---

**Análise:** Resposta correta. O assistente aplicou a Regra 4 (Passo 1): antes de qualquer cálculo, verificou se a data de abertura do chamado estava disponível no contexto da Seção 5. Como não estava, bloqueou a resposta e solicitou a informação — sem fornecer valores parciais, condicionais ou "na dúvida use o mais recente" (como o FAQ-08 sugere incorretamente).

**Resposta esperada após esclarecimento (ex.: "aberto em 15/01/2024"):**

> **Versão aplicável: PROC-042-v2** (chamado aberto após 01/12/2023).
>
> Cálculo:
> - Fator de peso para 600kg (faixa 500–1.000kg): **1.0**
> - Multiplicador regional Norte: **1.8**
> - Frete = Valor base × 1.8 × 1.0
>
> *(Fonte: PROC-042-v2, seções 2 e 2.1)*
>
> ⚠ Atenção: foram encontradas duas versões deste documento. Esta resposta usa PROC-042-v2 (novembro/2023) com base na data de abertura do chamado (15/01/2024). Confirme com a área responsável se o contrato do cliente referenciar versão anterior.

---

## Resumo das regras ativadas

| Pergunta | Regras ativadas | Comportamento esperado |
|---|---|---|
| Devolução de carga perigosa | Regra 2, Regra 5 | Resposta direta com fonte formal; FAQ citado apenas como alerta |
| SLA cliente Gold | Regra 6 | Solicitar tipo do chamado antes de responder |
| Frete 600kg Manaus | Regra 4, Regra 6 | Solicitar data de abertura antes de calcular |
