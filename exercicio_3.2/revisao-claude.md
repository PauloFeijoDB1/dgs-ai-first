# Revisão — `handler.ts`

> Baseado nas regras do `agents.md`: TypeScript strict mode · Zod · pino · sem dados pessoais no log · imports estáticos.

---

## 1. Import dinâmico → import estático

```diff
- // dentro da função
- const { CosmosClient } = require('@azure/cosmos');

+ // topo do arquivo
+ import { CosmosClient } from '@azure/cosmos';
```

---

## 2. `console.log` → pino

```diff
+ import pino from 'pino';
+ const logger = pino();

- console.log('Feedback recebido:', JSON.stringify(feedback));
+ logger.info({ queryId: feedback.queryId, rating: feedback.rating }, 'Feedback recebido');
```

---

## 3. Dado pessoal no log — remover `attendantEmail`

O objeto `feedback` contém e-mail. Nunca passar o objeto inteiro ao logger.

```diff
- logger.info({ ...feedback }, 'Feedback recebido'); // vaza attendantEmail
+ logger.info({ queryId: feedback.queryId, rating: feedback.rating }, 'Feedback recebido');
```

---

## 4. Validação de input com Zod

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

> O `as any` desaparece automaticamente — o tipo é inferido pelo Zod.

---

## Checklist

| # | Regra violada | Status |
|---|---|---|
| 1 | Imports estáticos no topo | ❌ `require` dinâmico dentro da função |
| 2 | `pino` para logging | ❌ uso de `console.log` |
| 3 | Nunca logar dados pessoais | ❌ `attendantEmail` no log |
| 4 | Zod para validação de input | ❌ `as any` sem validação |
| 5 | TypeScript strict mode | ⚠️ `as any` contradiz strict |
