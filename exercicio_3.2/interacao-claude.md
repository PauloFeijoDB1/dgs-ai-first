# Interação Claude — Revisão `handler.ts`

---

## Usuário

> **Arquivo enviado:** `handler.ts`
>
> dado a instrução no agents.md:
> _"TypeScript strict mode. Zod para validação de input. pino para logging (nunca console.log). Nunca logar dados pessoais (e-mail, nome). Imports estáticos no topo (nunca require dinâmico)."_
>
> dado o código em anexo, faça uma revisão

---

## Claude

Revisão do `handler.ts` identificando **4 violações diretas** das regras do `agents.md`, mais 1 ponto de atenção:

### 1. Import dinâmico → import estático

O `require('@azure/cosmos')` está dentro do corpo da função. Viola a regra de "imports estáticos no topo".

```diff
- const { CosmosClient } = require('@azure/cosmos'); // dentro da fn
+ import { CosmosClient } from '@azure/cosmos';      // topo do arquivo
```

### 2. `console.log` → pino

Uso direto de `console.log` é proibido. O logger do pino deve ser instanciado no módulo.

```diff
+ import pino from 'pino';
+ const logger = pino();

- console.log('Feedback recebido:', JSON.stringify(feedback));
+ logger.info({ queryId: feedback.queryId, rating: feedback.rating }, 'Feedback recebido');
```

### 3. Dado pessoal no log — `attendantEmail`

O objeto `feedback` contém `attendantEmail` e era passado inteiro ao log. E-mails devem ser omitidos explicitamente.

```diff
- logger.info({ ...feedback }, 'Feedback recebido'); // vaza attendantEmail
+ logger.info({ queryId: feedback.queryId, rating: feedback.rating }, 'Feedback recebido');
```

### 4. Validação de input com Zod ausente

O body era lido com `as any` e os campos usados diretamente sem validação.

```diff
+ import { z } from 'zod';

+ const FeedbackSchema = z.object({
+   queryId:        z.string().uuid(),
+   rating:         z.number().int().min(1).max(5),
+   comment:        z.string().max(2000).optional(),
+   attendantEmail: z.string().email(),
+ });

- const body = await request.json() as any;
+ const parsed = FeedbackSchema.safeParse(await request.json());
+ if (!parsed.success) return { status: 400, body: JSON.stringify(parsed.error.flatten()) };
+ const feedback = { ...parsed.data, timestamp: new Date().toISOString() };
```

### 5. (Atenção) TypeScript strict mode — uso de `any`

O cast `as any` contradiz strict mode. Com Zod, o tipo é inferido automaticamente e o `any` desaparece.

---

## Usuário

> crie um markdown resumido com os ajustes da revisão

---

## Claude

Gerado o arquivo `revisao-handler.md` com os 4 ajustes em formato diff + checklist:

```markdown
# Revisão — `handler.ts`

> Baseado nas regras do `agents.md`: TypeScript strict mode · Zod · pino · sem dados pessoais no log · imports estáticos.

## 1. Import dinâmico → import estático
## 2. `console.log` → pino
## 3. Dado pessoal no log — remover `attendantEmail`
## 4. Validação de input com Zod

| # | Regra violada | Status |
|---|---|---|
| 1 | Imports estáticos no topo | ❌ `require` dinâmico dentro da função |
| 2 | `pino` para logging | ❌ uso de `console.log` |
| 3 | Nunca logar dados pessoais | ❌ `attendantEmail` no log |
| 4 | Zod para validação de input | ❌ `as any` sem validação |
| 5 | TypeScript strict mode | ⚠️ `as any` contradiz strict |
```

---

## Usuário

> exporte essa interacao como interacao-claude.md

---

## Claude

Exportação da interação completa gerada como `interacao-claude.md`.

---

*Exportado em: 2026-06-27*
