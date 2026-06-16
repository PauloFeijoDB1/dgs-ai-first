# Evidencia de Interacao - Criacao da Skill Foundation

## Metadados

- Data: 2026-06-16
- Agente: GitHub Copilot (GPT-5.3-Codex)
- Workspace: `C:\DB1\DGS\AI First`
- Solicitacao do usuario: criar o `SKILL.md` da skill Foundation mais importante, com contexto, regras prescritivas, exemplos concretos (DO/DON'T com codigo) e anti-padroes.

## Prompt do Usuario

> "crie o SKILL.md da skill Foundation mais importante (a que sera usada por todas as outras como base). O arquivo deve conter: contexto, regras prescritivas, exemplos concretos (DO/DON'T com codigo), e anti-padroes"

## Passos Executados

1. Inspecao da estrutura de `skills/foundation` no starter repo.
2. Verificacao de que o arquivo aberto `skills/foundation/typescript-conventions.md` estava vazio.
3. Consulta de referencia em `dgs-ai-first/exercicio_2.3/foundation/typescript-conventions/SKILL.md` para manter padrao de qualidade.
4. Leitura de `package.json`, `tsconfig.json` e `README.md` do projeto `novatech-assistant` para alinhar stack e convencoes ao repositorio real.
5. Criacao do arquivo principal da skill Foundation em:
   - `Pratica 2/Anexo-D-starter-repo-novatech-assistant/novatech-assistant/skills/foundation/typescript-conventions/SKILL.md`
6. Validacao final do conteudo criado.

## Artefato Gerado

- Arquivo criado:
  - `Pratica 2/Anexo-D-starter-repo-novatech-assistant/novatech-assistant/skills/foundation/typescript-conventions/SKILL.md`

## Conteudo Entregue no SKILL.md

O arquivo criado inclui:

- Contexto e precedencia da skill base (Foundation global).
- Regras prescritivas obrigatorias:
  - tipagem e contratos
  - validacao de entrada
  - tratamento de erro
  - separacao de responsabilidades
  - imports/modulos
  - testes
  - nomenclatura/legibilidade
- Exemplos concretos com codigo em formato DO e DON'T para:
  - validacao de entrada HTTP
  - erro semantico vs erro generico
  - separacao de camadas
  - `unknown` + narrowing vs `any`
- Lista de anti-padroes proibidos.
- Checklist de uso antes de entrega.
- Orientacao de dependencia para skills filhas referenciando a Foundation.

## Resultado

Solicitacao concluida com sucesso: o `SKILL.md` base da Foundation foi criado e estruturado como baseline para todas as demais skills do projeto.

## Evidencia de Localizacao

- Diretorio solicitado para evidencia:
  - `dgs-ai-first/exercicio_2.3`
- Este arquivo de evidencia:
  - `dgs-ai-first/exercicio_2.3/interacao-copilot-criacao-skill-foundation.md`
