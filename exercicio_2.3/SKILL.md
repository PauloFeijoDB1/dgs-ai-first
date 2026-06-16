---
name: typescript-conventions
version: 1.0.0
owner: foundation
status: active
description: >
  Skill Foundation base e obrigatoria para qualquer geracao de codigo no
  novatech-assistant. Define convencoes prescritivas de TypeScript, tratamento
  de erros, validacao de entrada, organizacao em camadas e anti-padroes.
  Todas as skills (foundation, domain e artifact) devem aplicar estas regras.
---

# Foundation: TypeScript Conventions (Base Global)

## 1) Contexto

Esta e a skill Foundation mais importante do repositorio.

- Papel: baseline tecnico para qualquer implementacao em TypeScript.
- Escopo: todo codigo em `src/`, `tests/`, `specs` com exemplos de codigo e snippets em prompts.
- Projeto-alvo: `novatech-assistant`.
- Runtime e stack (conforme repo): Node.js ESM, TypeScript strict, Azure Functions v4, Vitest, Zod.

Regra de precedencia:

1. Este arquivo define o padrao global.
2. Skills de dominio podem especializar regras, mas nunca contradizer.
3. Em conflito, vence esta skill ate decisao explicita em ADR/AGENTS.

## 2) Regras Prescritivas (obrigatorias)

### 2.1 Tipagem e contratos

- Sempre usar `strict` e manter tipos explicitos nas fronteiras (entrada/saida de funcoes publicas).
- Nunca usar `any` em codigo novo.
- Preferir `unknown` + refinamento (type guard ou schema).
- DTOs e contratos de I/O devem ser definidos como `type` ou `interface` nomeados.

### 2.2 Validacao de entrada

- Toda entrada externa deve ser validada na borda (HTTP, fila, arquivo).
- Usar schema (Zod) antes de chamar servicos de negocio.
- Nao propagar payload cru para camadas internas.

### 2.3 Tratamento de erro

- Erros de dominio devem ser semanticos (ex.: `ValidationError`, `NotFoundError`).
- Handlers nao devem engolir excecoes.
- Retorno de erro ao cliente deve ser consistente e sem vazar stack trace.
- Logar contexto tecnico sem expor segredo, token, senha ou PII sensivel.

### 2.4 Separacao de responsabilidades

- Handler/Controller: parse, validacao, orquestracao e resposta.
- Service/UseCase: regra de negocio pura.
- Repository/Gateway: acesso externo (dados, APIs, storage).
- Nao misturar regra de negocio com detalhes de transporte HTTP.

### 2.5 Imports e modulos

- Projeto ESM: preferir imports ESM, sem `require`.
- Manter imports coesos e sem ciclos.
- Nao criar barrel files que escondam dependencia circular.

### 2.6 Testes

- Cada comportamento relevante de negocio deve ter teste.
- Teste deve validar comportamento observavel, nao detalhe interno.
- Evitar flaky tests (tempo real, dependencia externa nao isolada).

### 2.7 Nomenclatura e legibilidade

- Nomes devem comunicar intencao de negocio.
- Funcoes pequenas, com uma responsabilidade.
- Evitar abreviacoes opacas (`tmp`, `obj2`, `x1`).

## 3) Exemplos Concretos (DO / DON'T)

### 3.1 Entrada HTTP: validar antes de processar

DO:

```ts
import { z } from 'zod';

const AskSchema = z.object({
  question: z.string().min(3),
  customerId: z.string().uuid(),
});

export async function askHandler(req: Request) {
  const raw = await req.json();
  const input = AskSchema.parse(raw);

  const result = await askService.executar(input);
  return Response.json({ data: result }, { status: 200 });
}
```

DON'T:

```ts
export async function askHandler(req: Request) {
  const body: any = await req.json();
  const result = await askService.executar(body);
  return Response.json(result);
}
```

### 3.2 Erro semantico vs erro generico

DO:

```ts
export class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ValidationError';
  }
}

function ensurePositive(value: number): number {
  if (value <= 0) {
    throw new ValidationError('value must be greater than zero');
  }
  return value;
}
```

DON'T:

```ts
function ensurePositive(value: number): number {
  if (value <= 0) {
    throw new Error('invalid');
  }
  return value;
}
```

### 3.3 Separacao de camadas

DO:

```ts
// handler.ts
export async function createTicketHandler(req: Request) {
  const input = TicketSchema.parse(await req.json());
  const output = await createTicketService.executar(input);
  return Response.json(output, { status: 201 });
}

// create-ticket-service.ts
export async function executar(input: CreateTicketInput) {
  return ticketRepository.save({
    title: input.title,
    priority: input.priority,
  });
}
```

DON'T:

```ts
export async function createTicketHandler(req: Request) {
  const body = await req.json();

  // regra de negocio no handler
  if (!body.title || body.title.length < 5) {
    return Response.json({ error: 'invalid title' }, { status: 400 });
  }

  // acesso a dados no handler
  const saved = await db.collection('tickets').insertOne(body);
  return Response.json(saved, { status: 201 });
}
```

### 3.4 unknown + narrowing vs any

DO:

```ts
function toCustomerId(value: unknown): string {
  if (typeof value !== 'string' || value.length === 0) {
    throw new ValidationError('customerId must be a non-empty string');
  }
  return value;
}
```

DON'T:

```ts
function toCustomerId(value: any): string {
  return value;
}
```

## 4) Anti-padroes (proibidos)

1. `any` em fronteiras ou dominio sem justificativa documentada.
2. `try/catch` que suprime erro silenciosamente (`catch {}` ou `return null`).
3. Regras de negocio dentro de handler/controller.
4. Acesso direto a `process.env` espalhado no codigo (centralizar configuracao).
5. Logs com dados sensiveis (token, senha, CPF/email/telefone sem mascaramento).
6. Funcoes com multiplas responsabilidades e efeitos colaterais nao controlados.
7. Testes que dependem de tempo real/rede sem isolamento.
8. Copiar e colar validacoes em varios pontos em vez de reutilizar schema/funcao.

## 5) Checklist de uso desta skill (antes de entregar)

- Tipos de entrada/saida definidos e sem `any`.
- Validacao de entrada na borda com schema.
- Erros semanticos e resposta de erro consistente.
- Handler fino; regra em service/use case.
- Sem log de dado sensivel.
- Testes cobrindo fluxo feliz e falhas esperadas.

## 6) Como skills filhas devem referenciar esta base

Toda skill de dominio ou artifact deve incluir no inicio:

```md
Dependencias:
- foundation/typescript-conventions (obrigatoria)
```

E deve declarar explicitamente qualquer extensao local de regra (sem contradizer esta base).
