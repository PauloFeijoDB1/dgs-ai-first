"""
Pipeline de RAG — NovaTech
Módulo de Busca (Retrieval) e Montagem de Prompt
=================================================
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from ingestion import load_vector_store, ingest, DB_PATH
import os

# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Você é o Assistente de Atendimento da NovaTech, empresa de logística.
Responda dúvidas dos atendentes com base EXCLUSIVAMENTE nos trechos de documentação abaixo.

REGRAS OBRIGATÓRIAS:
1. Cite SEMPRE a fonte (doc_id + seção) para qualquer informação fornecida.
2. NUNCA invente prazos, valores, multiplicadores ou procedimentos.
   Se a informação não estiver nos trechos, diga: "Não encontrei essa informação na documentação disponível."
3. Quando houver duas versões do mesmo documento (PROC-042 v1 vs v2), use a MAIS RECENTE (v2),
   exceto para chamados abertos antes de 01/12/2023.
4. Documentos do tipo "informal" (FAQ) devem ser usados com cautela — indique isso ao atendente
   e recomende confirmar na documentação normativa.
5. Responda em português formal e objetivo.
6. Para carga perigosa: reforce SEMPRE que o processo é especial e o cliente deve contatar ramal 4500.

TRECHOS DE DOCUMENTAÇÃO RECUPERADOS:
{chunks_block}

---
PERGUNTA DO ATENDENTE: {question}

RESPOSTA (com citação de fonte obrigatória):"""


def search(question: str, store: dict, n_results: int = 5) -> list[dict]:
    """
    Busca os N chunks mais similares à pergunta usando TF-IDF + cosseno.
    
    Retorna lista de dicts com: chunk_id, text, similarity, metadata.
    """
    vectorizer = store["vectorizer"]
    tfidf_matrix = store["tfidf_matrix"]
    chunks = store["chunks"]

    # Embedding da pergunta
    q_vector = vectorizer.transform([question])

    # Similaridade cosseno (pergunta × todos os chunks)
    sims = cosine_similarity(q_vector, tfidf_matrix).flatten()

    # Top N índices por similaridade decrescente
    top_indices = np.argsort(sims)[::-1][:n_results]

    results = []
    for idx in top_indices:
        chunk = chunks[idx]
        results.append({
            "chunk_id": chunk["id"],
            "text": chunk["text"],
            "similarity": round(float(sims[idx]), 4),
            "metadata": chunk["metadata"],
        })

    return results


def format_chunks_block(retrieved: list[dict]) -> str:
    """Formata os chunks para inserção no prompt."""
    lines = []
    for i, chunk in enumerate(retrieved, 1):
        meta = chunk["metadata"]
        doc_id   = meta.get("doc_id", "?")
        version  = meta.get("version", "?")
        section  = meta.get("section", "?")
        doc_type = meta.get("type", "?")
        sim      = chunk["similarity"]
        warn     = " ⚠️ DOCUMENTO INFORMAL" if doc_type == "informal" else ""

        lines.append(
            f"[TRECHO {i} | {doc_id} v{version} | Seção: {section}"
            f" | Similaridade: {sim:.0%}{warn}]"
        )
        lines.append(chunk["text"])
        lines.append("")
    return "\n".join(lines)


def build_prompt(question: str, retrieved: list[dict]) -> str:
    chunks_block = format_chunks_block(retrieved)
    return SYSTEM_PROMPT.format(chunks_block=chunks_block, question=question)


def rag_query(question: str, store: dict, n_results: int = 5, verbose: bool = True) -> dict:
    """Pipeline completo: busca → monta prompt → retorna resultado."""
    retrieved = search(question, store, n_results=n_results)
    prompt = build_prompt(question, retrieved)

    if verbose:
        print(f"\n{'='*60}")
        print(f"PERGUNTA: {question}")
        print(f"{'─'*60}")
        print(f"{'#':<3} {'Doc':<20} {'Ver':<8} {'Seção':<30} {'Sim':<7} Tipo")
        print(f"{'─'*3} {'─'*20} {'─'*8} {'─'*30} {'─'*7} {'─'*8}")
        for i, r in enumerate(retrieved, 1):
            m = r["metadata"]
            print(
                f"{i:<3} {m.get('doc_id','?')[:20]:<20} "
                f"{m.get('version','?')[:8]:<8} "
                f"{m.get('section','?')[:30]:<30} "
                f"{r['similarity']:.0%}  "
                f"{m.get('type','?')[:8]}"
            )

    return {"question": question, "retrieved": retrieved, "prompt": prompt}


if __name__ == "__main__":
    store = load_vector_store() if os.path.exists(DB_PATH) else ingest(force=True)
    result = rag_query("Qual o prazo de devolução de mercadorias?", store)
    print("\n--- PROMPT GERADO ---")
    print(result["prompt"])
