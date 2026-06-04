# Simulação de Atendimento — Assistente NovaTech
> **Data de geração:** 2024-11 | **Fonte:** System Prompt v1.0 + Anexo B (Chunks de Referência RAG)

---

## Pergunta 1 — Prazo de devolução para carga perigosa

**Pergunta do atendente:**
> Qual o prazo de devolução para carga perigosa?

**Chunks recuperados:** POL-001-B (primário), POL-001-A (secundário), FAQ-03 (menor relevância)

---

### 1. Resposta Direta
Cargas perigosas **não são elegíveis para devolução pelo processo padrão**. Não se aplica o prazo de 7 dias úteis nesse caso.

### 2. Detalhamento
Cargas classificadas nas classes 1 a 6 da ANTT estão explicitamente excluídas do processo de devolução padrão. Isso inclui explosivos (classe 1), gases (classe 2), líquidos inflamáveis (classe 3), sólidos inflamáveis (classe 4), oxidantes e peróxidos (classe 5), e substâncias tóxicas e infectantes (classe 6). Cada caso deve ser tratado individualmente pelo setor de Gestão de Riscos.

### 3. Fontes
- → **POL-001-B, seção 3.2:** cargas perigosas classes 1–6 (ANTT) não são elegíveis para devolução padrão — tratamento individual pelo setor de Gestão de Riscos.
- → **POL-001-A, seção 3.1:** o prazo de 7 dias úteis se aplica ao processo padrão — do qual carga perigosa está excluída.

### 4. Alertas
> ⚠ O FAQ-03 menciona que o setor de Riscos já autorizou exceções em casos pontuais, mas isso **não altera a regra oficial**. Por ser fonte de menor confiabilidade (FAQ interno), não substitui a POL-001-B. Oriente o atendente a encaminhar ao ramal 4500 sem prometer exceção.

**Ação recomendada:** encaminhar para Gestão de Riscos — **ramal 4500**.

---

## Pergunta 2 — SLA de resolução para cliente Gold

**Pergunta do atendente:**
> Meu cliente é Gold, qual o SLA de resolução?

**Chunks recuperados:** SLA-2024-B (primário), SLA-2024-A (secundário), SLA-2024-C (relevante se incidente crítico)

---

### 1. Resposta Direta
Para clientes Gold, o SLA de resolução é de **até 24 horas úteis** para chamados gerais.

### 2. Detalhamento
Há dois cenários dependendo da natureza do chamado:

| Tipo de chamado | Resposta | Resolução |
|---|---|---|
| Chamado geral | até 2h úteis | até 24h úteis |
| Incidente crítico | até 30 minutos | até 4 horas |

Um chamado é considerado **incidente crítico** quando envolve:
- Carga com valor acima de R$ 100.000 com status desconhecido há mais de 6h
- Carga perigosa com irregularidade
- Mais de 5 chamados do mesmo cliente em 24h sobre o mesmo problema
- Qualquer risco à segurança de pessoas

### 3. Fontes
- → **SLA-2024-B, seção 2:** SLAs para chamados gerais — Gold: resposta 2h úteis, resolução 24h úteis.
- → **SLA-2024-C, seção 2:** SLAs para incidentes críticos — Gold: resposta 30min, resolução 4h.
- → **SLA-2024-D, seção 3:** definição de incidente crítico.

### 4. Alertas
> ⚠ Verifique a natureza do chamado antes de informar o SLA ao cliente — o prazo de resolução pode ser 4h ou 24h dependendo da classificação. Em caso de dúvida sobre a classificação, trate como incidente crítico e acione o supervisor.

---

## Pergunta 3 — Custo do frete para 600 kg para Manaus

**Pergunta do atendente:**
> Quanto custa o frete para 600kg para Manaus?

**Chunks recuperados:** PROC-042v2-A (primário), PROC-042v2-B (primário), PROC-042-A (risco de contradição), PROC-042-B (risco de contradição)

---

### 1. Resposta Direta
O valor exato do frete não pode ser calculado sem o **valor base da rota**, que não consta nos chunks disponíveis. Para um novo chamado, a fórmula aplicável é:

> **Frete = Valor base × 1,8 (Norte) × 1,0 (fator de peso)**

### 2. Detalhamento
Para um chamado novo (aberto a partir de 01/12/2023):

| Parâmetro | Valor |
|---|---|
| Multiplicador regional — Norte (Manaus) | 1,8 |
| Fator de peso — 600kg (faixa 500–1.000kg) | 1,0 |

Para obter o valor final, aplique essa fórmula sobre o **valor base da rota**, disponível na tabela comercial ou no sistema de precificação.

### 3. Fontes
- → **PROC-042v2-A, seção 2:** fórmula atualizada — Valor base × Multiplicador regional × Fator de peso; fator de peso 1,0 para 500–1.000kg.
- → **PROC-042v2-B, seção 2.1:** multiplicador regional Norte = 1,8 (versão novembro/2023).
- → **PROC-042v2-E, seção 5:** chamados a partir de 01/12/2023 usam os multiplicadores da v2.

### 4. Alertas
> ⚠ **Atenção: foram encontradas duas versões deste documento.** Esta resposta usa a versão mais recente (PROC-042-v2, novembro/2023). Se o contrato do cliente referenciar a versão anterior (v1), o multiplicador regional Norte seria 1,6 — confirme com a área Comercial.

> ⚠ Se este chamado foi **aberto antes de 01/12/2023** e ainda está em processamento, devem ser usados os multiplicadores da v1 (Norte = 1,6), conforme disposição transitória da PROC-042v2-E.

---

*Documento gerado a partir da simulação do Assistente de Atendimento NovaTech — System Prompt v1.0*
