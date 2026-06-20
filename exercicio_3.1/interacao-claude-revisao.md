# Revisão e Correção — `response-validator.ts`

**Data:** 20/06/2026  
**Arquivo revisado:** `src/services/response-validator.ts`  
**Projeto:** NovaTech Assistant

---

## Contexto

Revisão de código do validador determinístico de respostas do modelo de IA, responsável por garantir que outputs estruturados sigam o schema esperado e não violem a política de devolução de cargas perigosas.

---

## Problemas identificados no code review

### 1. Schema Zod aceita campos extras (sem `.strict()`)

O Zod, por padrão, opera em modo permissivo: qualquer campo não declarado no schema passa silenciosamente. Um payload com chaves inesperadas como `__proto__` ou `instruction` seria aceito sem aviso.

**Solução:** adicionar `.strict()` ao schema para rejeitar entradas com chaves desconhecidas.

---

### 2. Guarda de "carga perigosa + devolução" com cobertura fraca

As listas de termos nas três funções de detecção eram rígidas e perdiam variações legítimas do português:

| Variação | Coberta antes? |
|---|---|
| `"produtos perigosos"` | ❌ |
| `"material perigoso"` | ❌ |
| `"substância perigosa"` | ❌ |
| `"retorno"` / `"retornar"` | ❌ |
| `"reenvio"` / `"reenviar"` | ❌ |
| `"vedada"` / `"proibida"` | ❌ |

Qualquer reformulação do modelo que usasse termos fora da lista burla a guarda.

**Solução:** ampliar as três listas (`hasDangerousCargoAndReturnTopic`, `containsNegativeStatement`, `containsAffirmativeReturnForDangerousCargo`) com as variações mapeadas.

---

### 3. Validação de `source_document` fora do schema (inconsistência)

A verificação de espaços em branco (`!structured.source_document.trim()`) estava em `validateModelResponse`, fora do schema Zod. Isso criava duas fontes de verdade para as regras do mesmo campo.

**Solução:** mover a regra para o schema via `.refine()` e remover o bloco manual da função de validação.

---

## Correções aplicadas

### Schema — `.strict()` + `.refine()` centralizado

```typescript
// antes
export const structuredOutputSchema = z.object({
    answer: z.string().min(1, "answer é obrigatório"),
    source_document: z.string().min(1, "source_document é obrigatório"),
    confidence_score: z
        .number({ invalid_type_error: "confidence_score deve ser number" })
        .min(0, "confidence_score deve ser >= 0")
        .max(1, "confidence_score deve ser <= 1"),
});

// depois
export const structuredOutputSchema = z
    .object({
        answer: z.string().min(1, "answer é obrigatório"),
        source_document: z
            .string()
            .min(1, "source_document é obrigatório")
            .refine((v) => v.trim().length > 0, "source_document não pode ser apenas espaços"),
        confidence_score: z
            .number({ invalid_type_error: "confidence_score deve ser number" })
            .min(0, "confidence_score deve ser >= 0")
            .max(1, "confidence_score deve ser <= 1"),
    })
    .strict();
```

---

### `hasDangerousCargoAndReturnTopic` — termos ampliados

```typescript
// adicionados em mentionsDangerousCargo:
normalized.includes("produto perigoso") ||
normalized.includes("produtos perigosos") ||
normalized.includes("material perigoso") ||
normalized.includes("materiais perigosos") ||
normalized.includes("substancia perigosa") ||
normalized.includes("substancias perigosas");

// adicionados em mentionsReturn:
normalized.includes("retorno") ||
normalized.includes("retornar") ||
normalized.includes("reenvio") ||
normalized.includes("reenviar");
```

---

### `containsNegativeStatement` — variações adicionais

```typescript
// adicionados:
"nao e aceita",
"nao e aceito",
"nao sao aceitas",
"nao sao aceitos",
"impossivel realizar",
"e vedada",
"e vedado",
"sao vedadas",
"sao vedados",
"e proibida",
"e proibido",
"sao proibidas",
"sao proibidos",
"nao realiza",
"nao realizamos",
```

---

### `containsAffirmativeReturnForDangerousCargo` — variações adicionais

```typescript
// adicionados:
"retorno e possivel",
"retorno permitido",
"retorno e permitido",
"pode retornar",
"reenvio e possivel",
"reenvio permitido",
"reenvio e permitido",
"pode reenviar",
"aceita devolucao",
"aceito para devolucao",
"e aceita para retorno",
```

---

### `validateModelResponse` — verificação duplicada removida

```typescript
// bloco removido (regra agora vive no schema via .refine()):
if (!structured.source_document.trim()) {
    return logAndFallback(logger, "missing_source_document");
}
```

---

## Resumo das mudanças

| # | Problema | Severidade | Status |
|---|---|---|---|
| 1 | Schema aceita campos extras | Média | ✅ Corrigido |
| 2 | Cobertura fraca nas listas de termos | Alta | ✅ Corrigido |
| 3 | Validação de `source_document` fora do schema | Baixa | ✅ Corrigido |

---

## Arquivo final

O arquivo corrigido está em:  
`src/services/response-validator.ts`

Nenhuma interface pública foi alterada — `StructuredOutput`, `validateModelResponse` e `getDefaultRejectionMessage` mantêm as mesmas assinaturas.
