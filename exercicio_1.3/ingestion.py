"""
Pipeline de RAG — NovaTech
Módulo de Ingestão de Documentos
=================================
Responsável por:
  1. Ler arquivos .md da pasta docs/
  2. Dividir em chunks com estratégia híbrida semântico-estrutural
  3. Gerar embeddings com TF-IDF (scikit-learn) — zero dependências externas
  4. Armazenar vetores + textos + metadados (ChromaDB em memória/disco)

Estratégia de chunking: SEMÂNTICO-ESTRUTURAL
- Divide primariamente pelas seções Markdown (##, ###)
- Mantém tabelas e listas intactas dentro de cada seção
- Sub-divide seções longas (>800 chars) por parágrafo com overlap de 100 chars
- Preserva metadados: doc_id, versão, seção, tipo (normativo/informal)

Justificativa da estratégia:
  Chunking fixo (512 tokens) fragmentaria tabelas de multiplicadores regionais
  e listas de regras no meio de uma célula, degradando o retrieval. Documentos
  normativos são estruturados por seções com semântica própria — cada seção é
  uma unidade de conhecimento. Ao respeitar essa estrutura, cada chunk recuperado
  responde a uma intenção completa (ex: "regras de devolução de carga perigosa"),
  reduzindo alucinações por contexto incompleto.

  TF-IDF foi escolhido como embedding por:
  - Zero dependências de rede (sem download de modelos)
  - Excelente para domínio especializado com terminologia específica
    (nomes de documentos, siglas como CT-e, ANTT, classes de carga)
  - Em produção, substituir por sentence-transformers/all-MiniLM-L6-v2
    para capturar similaridade semântica além da lexical
"""

import os
import re
import json
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ── Configurações ─────────────────────────────────────────────────────────────
DOCS_DIR      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
DB_PATH       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vector_store.pkl")
MAX_CHUNK_CHARS = 800
OVERLAP_CHARS   = 100

# Metadados de cada arquivo — crítico para resolver ambiguidade de versões
DOC_METADATA = {
    "POL-001-politica-devolucao.md": {
        "doc_id": "POL-001",
        "version": "3.1",
        "date": "2024-01-15",
        "type": "normativo",
        "priority": 3,
    },
    "PROC-042-frete-especial-v1.md": {
        "doc_id": "PROC-042-v1",
        "version": "1.0",
        "date": "2023-03-03",
        "type": "normativo",
        "priority": 1,          # BAIXA — versão antiga, superada pela v2
        "superseded_by": "PROC-042-v2",
    },
    "PROC-042-v2-frete-especial-revisado.md": {
        "doc_id": "PROC-042-v2",
        "version": "2.0",
        "date": "2023-11-10",
        "type": "normativo",
        "priority": 3,
    },
    "SLA-2024-tabela-sla-clientes.md": {
        "doc_id": "SLA-2024",
        "version": "2024.1",
        "date": "2024-01-02",
        "type": "contratual",
        "priority": 3,
    },
    "FAQ-atendimento.md": {
        "doc_id": "FAQ",
        "version": "informal",
        "date": "N/A",
        "type": "informal",
        "priority": 1,          # BAIXA — não validado pelo Compliance
    },
}


def split_into_chunks(text: str, filename: str) -> list[dict]:
    """Divide o documento em chunks semântico-estruturais."""
    doc_meta = DOC_METADATA.get(filename, {
        "doc_id": filename.replace(".md", ""),
        "version": "?",
        "date": "?",
        "type": "desconhecido",
        "priority": 1,
    })

    chunks = []
    # Divide nas seções Markdown (# ## ###)
    sections = re.split(r'(?=^#{1,3} )', text, flags=re.MULTILINE)

    current_h2 = ""
    chunk_index = 0

    for section in sections:
        section = section.strip()
        if not section:
            continue

        header_match = re.match(r'^(#{1,3})\s+(.+)', section)
        header_text = header_match.group(2).strip() if header_match else "Introdução"
        header_level = len(header_match.group(1)) if header_match else 1

        if header_level <= 2:
            current_h2 = header_text

        def make_chunk(content: str) -> dict:
            nonlocal chunk_index
            cid = f"{doc_meta['doc_id']}-chunk-{chunk_index:03d}"
            chunk_index += 1
            return {
                "id": cid,
                "text": content.strip(),
                "metadata": {
                    **{k: v for k, v in doc_meta.items()},
                    "filename": filename,
                    "section": header_text,
                    "parent_section": current_h2,
                    "chunk_index": chunk_index - 1,
                    "char_count": len(content.strip()),
                },
            }

        if len(section) <= MAX_CHUNK_CHARS:
            chunks.append(make_chunk(section))
        else:
            # Sub-divide por parágrafo com overlap
            paragraphs = re.split(r'\n{2,}', section)
            current = ""
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                if len(current) + len(para) + 2 <= MAX_CHUNK_CHARS:
                    current = (current + "\n\n" + para).strip()
                else:
                    if current:
                        chunks.append(make_chunk(current))
                        overlap = current[-OVERLAP_CHARS:] if len(current) > OVERLAP_CHARS else current
                        current = overlap + "\n\n" + para
                    else:
                        current = para
            if current:
                chunks.append(make_chunk(current))

    return chunks


def load_documents() -> list[dict]:
    all_chunks = []
    for fn in sorted(os.listdir(DOCS_DIR)):
        if not fn.endswith(".md"):
            continue
        with open(os.path.join(DOCS_DIR, fn), encoding="utf-8") as f:
            text = f.read()
        chunks = split_into_chunks(text, fn)
        all_chunks.extend(chunks)
        print(f"  [{fn}] → {len(chunks)} chunks")
    return all_chunks


def ingest(force: bool = False):
    """Executa o pipeline completo de ingestão."""
    print("=" * 60)
    print("PIPELINE DE INGESTÃO — NovaTech RAG")
    print("=" * 60)

    if os.path.exists(DB_PATH) and not force:
        print(f"\n⚡ Vector store já existe em {DB_PATH}")
        print("   Use ingest(force=True) para reindexar.")
        return load_vector_store()

    # 1. Carrega e chunkifica documentos
    print("\n[1/3] Lendo e chunkificando documentos...")
    chunks = load_documents()
    print(f"\n      Total: {len(chunks)} chunks de {len(DOC_METADATA)} documentos")

    # 2. Gera embeddings TF-IDF
    print("\n[2/3] Gerando embeddings TF-IDF...")
    texts = [c["text"] for c in chunks]
    
    # Configuração do TF-IDF: bi-gramas para capturar frases ("dias úteis", "carga perigosa")
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),     # uni + bi-gramas
        min_df=1,
        max_df=0.95,
        sublinear_tf=True,      # escala logarítmica para freq. de termos
        analyzer="word",
    )
    tfidf_matrix = vectorizer.fit_transform(texts)
    print(f"      Matriz TF-IDF: {tfidf_matrix.shape[0]} docs × {tfidf_matrix.shape[1]} features")

    # 3. Persiste no disco
    print("\n[3/3] Salvando vector store...")
    store = {
        "chunks": chunks,
        "vectorizer": vectorizer,
        "tfidf_matrix": tfidf_matrix,
    }
    with open(DB_PATH, "wb") as f:
        pickle.dump(store, f)
    print(f"      Salvo em: {DB_PATH}")

    print(f"\n✅ Ingestão concluída! {len(chunks)} chunks indexados.")
    return store


def load_vector_store() -> dict:
    with open(DB_PATH, "rb") as f:
        return pickle.load(f)


if __name__ == "__main__":
    ingest(force=True)
