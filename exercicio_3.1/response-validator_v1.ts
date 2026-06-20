import { z } from "zod";

const DEFAULT_REJECTION_MESSAGE =
	"Desculpe, não consegui validar a resposta com segurança. Tente novamente em instantes.";

const SAFE_FALLBACK_SOURCE_DOCUMENT = "POL-001-politica-devolucao.md";

// Structured output obrigatório do modelo.
export const structuredOutputSchema = z.object({
	answer: z.string().min(1, "answer é obrigatório"),
	source_document: z.string().min(1, "source_document é obrigatório"),
	confidence_score: z
		.number({ invalid_type_error: "confidence_score deve ser number" })
		.min(0, "confidence_score deve ser >= 0")
		.max(1, "confidence_score deve ser <= 1"),
});

export type StructuredOutput = z.infer<typeof structuredOutputSchema>;

export type ResponseValidationLogger = {
	warn: (payload: Record<string, unknown>, message: string) => void;
};

export const SAFE_FALLBACK_RESPONSE: StructuredOutput = {
	answer: DEFAULT_REJECTION_MESSAGE,
	source_document: SAFE_FALLBACK_SOURCE_DOCUMENT,
	confidence_score: 0,
};

function normalizeText(value: string): string {
	return value
		.toLowerCase()
		.normalize("NFD")
		.replace(/[\u0300-\u036f]/g, "");
}

function hasDangerousCargoAndReturnTopic(answer: string): boolean {
	const normalized = normalizeText(answer);
	const mentionsDangerousCargo =
		normalized.includes("carga perigosa") ||
		normalized.includes("cargas perigosas") ||
		normalized.includes("mercadoria perigosa") ||
		normalized.includes("mercadorias perigosas");

	const mentionsReturn =
		normalized.includes("devolucao") ||
		normalized.includes("devolver") ||
		normalized.includes("devolvida") ||
		normalized.includes("devolvidas");

	return mentionsDangerousCargo && mentionsReturn;
}

function containsNegativeStatement(answer: string): boolean {
	const normalized = normalizeText(answer);

	return [
		"nao e elegivel",
		"nao sao elegiveis",
		"nao e possivel",
		"nao pode",
		"nao podem",
		"nao permitido",
		"nao permitida",
		"nao permitidas",
		"nao permitidos",
		"nao pelo processo padrao",
		"deve entrar em contato com gestao de riscos",
		"ramal 4500",
	].some((clause) => normalized.includes(clause));
}

function containsAffirmativeReturnForDangerousCargo(answer: string): boolean {
	const normalized = normalizeText(answer);

	return [
		"devolucao e possivel",
		"devolucao de carga perigosa e possivel",
		"pode devolver carga perigosa",
		"pode ser devolvida",
		"devolucao permitida",
		"devolucao e permitida",
		"e elegivel para devolucao",
	].some((clause) => normalized.includes(clause));
}

function parseStructuredOutput(payload: string): { data: StructuredOutput } | { error: string } {
	let parsedJson: unknown;

	try {
		parsedJson = JSON.parse(payload);
	} catch {
		return { error: "invalid_json" };
	}

	const parsed = structuredOutputSchema.safeParse(parsedJson);
	if (!parsed.success) {
		return {
			error: `schema_validation_failed:${parsed.error.issues
				.map((issue) => `${issue.path.join(".") || "root"}:${issue.message}`)
				.join("|")}`,
		};
	}

	return { data: parsed.data };
}

function logAndFallback(logger: ResponseValidationLogger, reason: string): StructuredOutput {
	logger.warn(
		{
			reason,
			fallback_source_document: SAFE_FALLBACK_RESPONSE.source_document,
		},
		"Model response rejected by deterministic validator",
	);

	return SAFE_FALLBACK_RESPONSE;
}

export function validateModelResponse(
	rawResponse: string,
	logger: ResponseValidationLogger,
): StructuredOutput {
	const parseResult = parseStructuredOutput(rawResponse);
	if ("error" in parseResult) {
		return logAndFallback(logger, parseResult.error);
	}

	const structured = parseResult.data;

	if (!structured.source_document.trim()) {
		return logAndFallback(logger, "missing_source_document");
	}

	const mustApplyDangerousReturnGuard = hasDangerousCargoAndReturnTopic(structured.answer);
	if (mustApplyDangerousReturnGuard) {
		const hasNegative = containsNegativeStatement(structured.answer);
		const hasAffirmative = containsAffirmativeReturnForDangerousCargo(structured.answer);

		if (!hasNegative || hasAffirmative) {
			return logAndFallback(logger, "dangerous_cargo_return_policy_violation");
		}
	}

	return structured;
}

export function getDefaultRejectionMessage(): string {
	return DEFAULT_REJECTION_MESSAGE;
}
