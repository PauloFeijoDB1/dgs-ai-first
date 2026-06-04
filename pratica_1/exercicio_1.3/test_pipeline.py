"""
Pipeline de RAG — NovaTech
Testes com 7 perguntas do mapa de cobertura (Anexo B)
======================================================
"""

import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ingestion import load_vector_store, DB_PATH
from retrieval import rag_query, search

# ── Gabarito do Anexo B ───────────────────────────────────────────────────────
TESTS = [
    {
        "id": "Q1",
        "pergunta": "Qual o prazo de devolução?",
        "docs_esperados": ["POL-001"],
        "secoes_chave": ["3.1", "Prazo geral", "3.2", "Exceções"],
        "resposta_esperada": "7 dias úteis; cargas perigosas são exceção",
        "armadilha": False,
        "notas": "Deve recuperar seção 3.1 (prazo) e 3.2 (exceções perigosas)",
    },
    {
        "id": "Q2",
        "pergunta": "Posso devolver carga perigosa?",
        "docs_esperados": ["POL-001"],
        "secoes_chave": ["3.2", "Exceções"],
        "resposta_esperada": "NÃO — não elegível para processo padrão; ligar ramal 4500",
        "armadilha": True,
        "notas": "Armadilha: FAQ-03 diz 'não diga que é impossível'. Política oficial: NÃO.",
    },
    {
        "id": "Q3",
        "pergunta": "Qual o SLA do cliente Gold?",
        "docs_esperados": ["SLA-2024"],
        "secoes_chave": ["Tabela de SLAs", "SLA", "2"],
        "resposta_esperada": "Resposta 2h úteis, resolução 24h úteis (geral); 30min/4h (crítico)",
        "armadilha": False,
        "notas": "Deve recuperar SLA-2024 com a tabela de SLAs",
    },
    {
        "id": "Q4",
        "pergunta": "Qual o multiplicador de frete para o Sudeste?",
        "docs_esperados": ["PROC-042-v2"],
        "secoes_chave": ["Multiplicadores regionais", "2.1"],
        "resposta_esperada": "1.1 (v2, novembro/2023); v1 dizia 1.0 — RISCO DE CONTRADIÇÃO",
        "armadilha": True,
        "notas": "Armadilha: v1 diz 1.0, v2 diz 1.1. Deve retornar v2.",
    },
    {
        "id": "Q5",
        "pergunta": "Qual o prazo adicional de entrega para frete especial?",
        "docs_esperados": ["PROC-042-v2"],
        "secoes_chave": ["Prazo", "3"],
        "resposta_esperada": "+3 dias úteis (v2); v1 dizia +2 dias — RISCO DE CONTRADIÇÃO",
        "armadilha": True,
        "notas": "Armadilha: v1 diz +2 dias, v2 diz +3 dias. Deve retornar v2.",
    },
    {
        "id": "Q6",
        "pergunta": "Qual o SLA do cliente Platinum?",
        "docs_esperados": ["SLA-2024"],  # deve dizer que Platinum não existe
        "secoes_chave": ["Classificação", "tiers"],
        "resposta_esperada": "Tier Platinum NÃO existe — apenas Gold, Silver e Standard",
        "armadilha": True,
        "notas": "Tier inexistente. Assistente não deve inventar SLA para Platinum.",
    },
    {
        "id": "Q7",
        "pergunta": "Qual o valor do frete para 300kg para Salvador?",
        "docs_esperados": [],  # sem cobertura — frete padrão < 500kg
        "secoes_chave": [],
        "resposta_esperada": "Informação não encontrada na base — frete padrão (<500kg) não documentado",
        "armadilha": True,
        "notas": "Pergunta sem cobertura. Assistente deve dizer que não encontrou, não inventar.",
    },
]


def evaluate(retrieved: list[dict], test: dict) -> dict:
    """Avalia qualidade do retrieval contra o gabarito."""
    doc_ids = [r["metadata"].get("doc_id", "") for r in retrieved]
    docs_esp = test["docs_esperados"]

    # Docs esperados encontrados?
    docs_ok = [d for d in docs_esp if any(d in rid for rid in doc_ids)]
    recall = len(docs_ok) / len(docs_esp) if docs_esp else (0.0 if doc_ids else 1.0)

    # Contaminação v1 (versão antiga da PROC-042)?
    v1_contam = any("PROC-042-v1" in rid for rid in doc_ids)

    # Informal no topo?
    top_informal = retrieved[0]["metadata"].get("type") == "informal" if retrieved else False

    if not docs_esp:
        # Pergunta sem cobertura: ideal seria NÃO recuperar docs normativos confiantes
        status = "⚠️  SEM COBERTURA"
    elif recall >= 0.8:
        status = "✅ BOM"
    elif recall >= 0.5:
        status = "⚠️  PARCIAL"
    else:
        status = "❌ RUIM"

    return {
        "doc_ids_recuperados": doc_ids,
        "docs_ok": docs_ok,
        "recall": round(recall, 2),
        "v1_contaminacao": v1_contam,
        "top_informal": top_informal,
        "status": status,
    }


def run_tests():
    print("=" * 70)
    print("TESTES DO PIPELINE DE RAG — NovaTech (7 perguntas do Anexo B)")
    print("=" * 70)

    store = load_vector_store() if os.path.exists(DB_PATH) else None
    if not store:
        from ingestion import ingest
        store = ingest(force=True)

    all_results = []
    all_prompts = []

    for test in TESTS:
        tag = " [ARMADILHA]" if test["armadilha"] else ""
        print(f"\n{'─'*70}")
        print(f"TESTE {test['id']}{tag}: {test['pergunta']}")
        print(f"Notas: {test['notas']}")
        print("─" * 70)

        result = rag_query(test["pergunta"], store, n_results=5, verbose=True)
        ev = evaluate(result["retrieved"], test)

        print(f"\n  Avaliação retrieval:")
        print(f"    Docs esperados : {test['docs_esperados'] or '(nenhum — sem cobertura)'}")
        print(f"    Docs OK        : {ev['docs_ok']}")
        print(f"    Recall         : {ev['recall']:.0%}")
        print(f"    Contam. v1     : {'⚠️  SIM' if ev['v1_contaminacao'] else '✅ NÃO'}")
        print(f"    Informal no topo: {'⚠️  SIM' if ev['top_informal'] else '✅ NÃO'}")
        print(f"    Status         : {ev['status']}")
        print(f"\n  Resposta esperada: {test['resposta_esperada']}")

        print(f"\n{'·'*40}")
        print("PROMPT GERADO (para envio ao LLM):")
        print('·' * 40)
        print(result["prompt"])

        all_results.append({**test, "evaluation": ev})
        all_prompts.append({"id": test["id"], "pergunta": test["pergunta"], "prompt": result["prompt"]})

    # Resumo
    print(f"\n{'='*70}")
    print("RESUMO DOS 7 TESTES")
    print("=" * 70)
    print(f"{'ID':<5} {'Pergunta':<48} {'Status':<15} {'Recall':<8} {'v1?'}")
    print(f"{'─'*5} {'─'*48} {'─'*15} {'─'*8} {'─'*5}")
    for r in all_results:
        ev = r["evaluation"]
        pergunta_curta = r["pergunta"][:48]
        v1 = "⚠️" if ev["v1_contaminacao"] else "✅"
        print(f"{r['id']:<5} {pergunta_curta:<48} {ev['status']:<15} {str(round(ev['recall']*100))+'%':<8} {v1}")

    # Salva resultados
    results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_results.json")
    prompts_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_prompts.txt")

    with open(results_path, "w", encoding="utf-8") as f:
        slim = [{k: v for k, v in r.items()} for r in all_results]
        json.dump(slim, f, ensure_ascii=False, indent=2)

    with open(prompts_path, "w", encoding="utf-8") as f:
        for p in all_prompts:
            f.write(f"\n{'='*70}\n")
            f.write(f"TESTE {p['id']}: {p['pergunta']}\n")
            f.write("=" * 70 + "\n\n")
            f.write(p["prompt"])
            f.write("\n")

    print(f"\n📁 Arquivos salvos:")
    print(f"   {results_path}")
    print(f"   {prompts_path}")
    return all_results


if __name__ == "__main__":
    run_tests()
