# Interação — Revisão Crítica do Scaffold TASK-001

**Contexto:** Revisão técnica do código gerado para o endpoint de query (Azure Functions v4)  
**Data:** 13 jun 2026  
**Recorte:** A partir da solicitação "Revise criticamente o código gerado..."

---

## Solicitação do usuário

> Revise criticamente o código gerado, identifique ao menos 2 pontos que precisariam de ajuste antes de um code review real

---

## Resposta de revisão crítica

### Achados (ordem de severidade)

1. Alto: há duas implementações concorrentes para query, uma ativa e outra legada que lança erro.
A versão nova está em `src/functions/query.ts`, mas ainda existe o stub antigo em `src/functions/query/handler.ts` com `throw Not implemented`.
Risco real: alguém referenciar o módulo antigo na orquestração das próximas tasks e quebrar o fluxo em runtime.
Ajuste sugerido: remover o legado ou consolidar tudo em um único caminho de implementação para eliminar ambiguidade.

2. Médio: endpoint exposto como `anonymous` sem evidência de decisão de segurança para ambiente real.
A configuração atual está em `src/functions/query.ts`.
Para scaffold local é aceitável, mas em code review real isso normalmente pede ajuste/documentação explícita de proteção (APIM, Function key, Easy Auth etc.) antes de promover para ambientes superiores.
Ajuste sugerido: parametrizar `authLevel` por ambiente ou registrar decisão arquitetural no README/ADR.

3. Médio: configuração local depende de storage emulator sem orientação operacional.
`local.settings.json` usa `UseDevelopmentStorage=true`, o que exige Azurite ativo.
Sem isso, a validação local do endpoint tende a falhar mesmo com código correto.
Ajuste sugerido: documentar pré-requisito (Azure Functions Core Tools + Azurite) no README e incluir exemplo de startup local.

### Resumo curto

O scaffold está correto para TASK-001, mas antes de um code review real os principais ajustes são:
- eliminar duplicidade de implementação
- formalizar segurança do endpoint por ambiente
- documentar pré-requisitos operacionais para execução local
