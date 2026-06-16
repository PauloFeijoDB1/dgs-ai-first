# Mapeamento de Criação e Consumo — Skills NovaTech Assistant

> Hierarquia Foundation → Domain → Artifact  
> Para cada skill: quem cria, quem consome (papel humano + agente), e frequência de uso estimada.

---

## Foundation

### `typescript-conventions` ⭐ — base obrigatória para todas as skills

| Campo | Valor |
|---|---|
| **Caminho** | `skills/foundation/typescript-conventions/SKILL.md` |
| **Quem cria** | Tech Lead |
| **Consome — papéis** | Dev Backend, Dev Frontend, QA |
| **Consome — agentes** | GitHub Copilot, Claude Code, qualquer agente que gere `.ts`/`.tsx` |
| **Frequência** | ████████████ Alta — base de todo artefato TypeScript do projeto |

---

## Domain

### `azure-functions-api`

| Campo | Valor |
|---|---|
| **Caminho** | `skills/domain/api/SKILL.md` |
| **Quem cria** | Tech Lead + Dev Backend Sênior |
| **Consome — papéis** | Dev Backend, Arquiteto de Soluções |
| **Consome — agentes** | GitHub Copilot, agente de code review |
| **Frequência** | ████████████ Alta — acionada a cada novo endpoint |

### `integration-test`

| Campo | Valor |
|---|---|
| **Caminho** | `skills/domain/test/SKILL.md` |
| **Quem cria** | Dev Backend Sênior + QA Lead |
| **Consome — papéis** | Dev Backend, QA |
| **Consome — agentes** | GitHub Copilot, Claude Code |
| **Frequência** | ████████████ Alta — par obrigatório de todo endpoint |

### `react-frontend`

| Campo | Valor |
|---|---|
| **Caminho** | `skills/domain/frontend/SKILL.md` |
| **Quem cria** | Tech Lead + Dev Frontend Sênior |
| **Consome — papéis** | Dev Frontend |
| **Consome — agentes** | GitHub Copilot, Claude Code, agente design→código |
| **Frequência** | ████████░░░░ Média — por sprint de painel web |

### `technical-docs`

| Campo | Valor |
|---|---|
| **Caminho** | `skills/domain/docs/SKILL.md` |
| **Quem cria** | Tech Lead |
| **Consome — papéis** | Dev, PM, Arquiteto |
| **Consome — agentes** | Claude Chat |
| **Frequência** | █████░░░░░░░ Baixa-Média — por decisão de arquitetura relevante |

---

## Artifact

### `rag-endpoint`

| Campo | Valor |
|---|---|
| **Caminho** | `skills/artifact/rag-endpoint/SKILL.md` |
| **Quem cria** | Tech Lead + Dev Backend Sênior |
| **Consome — papéis** | Dev Backend |
| **Consome — agentes** | GitHub Copilot, Claude Code, agente de scaffolding |
| **Frequência** | ████████████ Alta — vários endpoints RAG ao longo do projeto |

### `integration-test` (artifact)

| Campo | Valor |
|---|---|
| **Caminho** | `skills/artifact/integration-test/SKILL.md` |
| **Quem cria** | Dev Backend Sênior + QA Lead |
| **Consome — papéis** | Dev Backend, QA |
| **Consome — agentes** | GitHub Copilot, Claude Code |
| **Frequência** | ████████████ Alta — 1 arquivo de teste por endpoint gerado |

### `react-component`

| Campo | Valor |
|---|---|
| **Caminho** | `skills/artifact/react-component/SKILL.md` |
| **Quem cria** | Dev Frontend Sênior |
| **Consome — papéis** | Dev Frontend |
| **Consome — agentes** | GitHub Copilot, Claude Code |
| **Frequência** | ████████░░░░ Média — por feature de painel web |

### `tech-doc`

| Campo | Valor |
|---|---|
| **Caminho** | `skills/artifact/tech-doc/SKILL.md` |
| **Quem cria** | Tech Lead |
| **Consome — papéis** | Dev, PM, Arquiteto |
| **Consome — agentes** | Claude Chat |
| **Frequência** | █████░░░░░░░ Baixa-Média — por decisão ou módulo novo |

### `product-spec`

| Campo | Valor |
|---|---|
| **Caminho** | `skills/artifact/product-spec/SKILL.md` |
| **Quem cria** | PM + Tech Lead (revisão) |
| **Consome — papéis** | PM, Tech Lead, Designer |
| **Consome — agentes** | Claude Chat |
| **Frequência** | ███░░░░░░░░░ Baixa — por épico ou feature grande |

---

## Visão consolidada

| Skill | Tier | Quem cria | Papéis consumidores | Agentes consumidores | Frequência |
|---|---|---|---|---|---|
| `typescript-conventions` ⭐ | Foundation | Tech Lead | Dev Backend, Dev Frontend, QA | Copilot, Claude Code, qualquer agente `.ts` | Alta |
| `azure-functions-api` | Domain | Tech Lead, Dev Backend Sênior | Dev Backend, Arquiteto | Copilot, agente code review | Alta |
| `integration-test` | Domain | Dev Backend Sênior, QA Lead | Dev Backend, QA | Copilot, Claude Code | Alta |
| `react-frontend` | Domain | Tech Lead, Dev Frontend Sênior | Dev Frontend | Copilot, Claude Code, agente design→código | Média |
| `technical-docs` | Domain | Tech Lead | Dev, PM, Arquiteto | Claude Chat | Baixa-Média |
| `rag-endpoint` | Artifact | Tech Lead, Dev Backend Sênior | Dev Backend | Copilot, Claude Code, agente scaffolding | Alta |
| `integration-test` | Artifact | Dev Backend Sênior, QA Lead | Dev Backend, QA | Copilot, Claude Code | Alta |
| `react-component` | Artifact | Dev Frontend Sênior | Dev Frontend | Copilot, Claude Code | Média |
| `tech-doc` | Artifact | Tech Lead | Dev, PM, Arquiteto | Claude Chat | Baixa-Média |
| `product-spec` | Artifact | PM, Tech Lead (revisão) | PM, Tech Lead, Designer | Claude Chat | Baixa |

---

## Padrões observados

**Concentração de criação no Tech Lead** — responsável por 6 das 10 skills. As skills que definem convenções precisam de autoridade arquitetural para não virarem documentos de consenso diluído.

**PM só aparece como criador em `product-spec`** — única skill que não exige formação técnica para criar. As demais skills são consumidas pelo PM (como papéis de leitura), nunca criadas por ele.

**`Claude Chat` vs `GitHub Copilot`** — skills de geração de código (api, test, rag, react) são consumidas pelo Copilot inline no editor. Skills de documentação e spec são consumidas pelo Claude Chat em conversa, porque o output é texto estruturado, não código.

**Frequência reflete o ciclo real do projeto** — `rag-endpoint` e `integration-test` têm frequência Alta porque todo sprint gera ao menos um endpoint RAG e seu par de testes. `product-spec` tem frequência Baixa porque SDD só aparece na discovery de features grandes.
