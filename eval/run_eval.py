from app.config import settings
from app.search import DocumentVectorSearch
import os
import sys
import json
import time
import argparse
import numpy as np
from typing import List, Dict, Any

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def normalize_text(text: str) -> str:
    """Padroniza o texto ignorando maiúsculas, minúsculas e espaços nas pontas."""
    return text.strip().lower()


def compute_hits(retrieved_dishes: List[str], relevant_dishes: List[str]) -> Dict[str, int]:
    """Calcula se pelo menos um prato relevante aparece no top k (Hit@1, Hit@3, Hit@5)."""
    norm_relevant = {normalize_text(d) for d in relevant_dishes}

    hits = {"hit_1": 0, "hit_3": 0, "hit_5": 0}

    for k, key in [(1, "hit_1"), (3, "hit_3"), (5, "hit_5")]:
        top_k = [normalize_text(d) for d in retrieved_dishes[:k]]
        if any(d in norm_relevant for d in top_k):
            hits[key] = 1

    return hits


def compute_recall(retrieved_dishes: List[str], relevant_dishes: List[str], k: int) -> float:
    """Calcula o Recall@k: fração dos pratos relevantes encontrados no top k."""
    if not relevant_dishes:
        return 0.0

    norm_relevant = {normalize_text(d) for d in relevant_dishes}
    top_k = [normalize_text(d) for d in retrieved_dishes[:k]]

    found = sum(1 for d in top_k if d in norm_relevant)
    return found / len(norm_relevant)


def compute_mrr(retrieved_dishes: List[str], relevant_dishes: List[str]) -> float:
    """Calcula o MRR (Mean Reciprocal Rank): 1 / posição do primeiro prato relevante."""
    norm_relevant = {normalize_text(d) for d in relevant_dishes}

    for i, dish in enumerate(retrieved_dishes):
        if normalize_text(dish) in norm_relevant:
            return 1.0 / (i + 1)

    return 0.0


def run_evaluation(model_name: str, min_score: float, queries_path: str) -> Dict[str, Any]:
    print(
        f"\n--- Avaliando com o modelo: {model_name} (min_score: {min_score}) ---")

    if not os.path.exists(queries_path):
        print(f"Erro: Arquivo de consultas não encontrado em {queries_path}")
        return {}

    with open(queries_path, 'r', encoding='utf-8') as f:
        queries_data = json.load(f)

    searcher = DocumentVectorSearch(model_name=model_name)
    searcher.load_documents(settings.DATA_PATH)
    searcher.process_documents()

    metrics_records = []
    query_details = []
    latencies = []

    out_of_scope_scores = []
    normal_scores = []
    rejected_out_of_scope_count = 0
    total_out_of_scope = 0

    for item in queries_data:
        qid = item.get("id")
        query_text = item.get("query")
        relevant_dishes = item.get("relevant_dishes", [])
        is_out_of_scope = item.get("out_of_scope", False)

        # Mede a latência da busca (excluindo carga inicial)
        start_time = time.time()
        # Busca sem o min_score fixo para capturar os scores brutos
        results = searcher.query(query_text, num_results=5, min_score=0.0)
        end_time = time.time()

        latency_ms = (end_time - start_time) * 1000
        latencies.append(latency_ms)

        retrieved_names = [r.get("Dish Name") or r.get(
            "dish_name", "") for r in results]
        best_score = results[0].get("score", 0.0) if results else 0.0

        if is_out_of_scope:
            total_out_of_scope += 1
            out_of_scope_scores.append(best_score)
            # Verifica se foi rejeitado corretamente (melhor score abaixo do min_score)
            if best_score < min_score:
                rejected_out_of_scope_count += 1

            query_details.append({
                "id": qid,
                "query": query_text,
                "type": "out_of_scope",
                "best_score": best_score,
                "rejected_correctly": best_score < min_score,
                "top_3_retrieved": retrieved_names[:3]
            })
        else:
            if not relevant_dishes:
                print(
                    f"Aviso: Consulta normal {qid} ('{query_text}') sem relevant_dishes definidos. Ignorando nas métricas de relevância.")
                continue

            if results:
                normal_scores.append(best_score)

            hits = compute_hits(retrieved_names, relevant_dishes)
            rec_3 = compute_recall(retrieved_names, relevant_dishes, 3)
            rec_5 = compute_recall(retrieved_names, relevant_dishes, 5)
            mrr = compute_mrr(retrieved_names, relevant_dishes)

            metrics_records.append({
                "hit_1": hits["hit_1"],
                "hit_3": hits["hit_3"],
                "hit_5": hits["hit_5"],
                "recall_3": rec_3,
                "recall_5": rec_5,
                "mrr": mrr
            })

            query_details.append({
                "id": qid,
                "query": query_text,
                "type": "normal",
                "hit_1": hits["hit_1"],
                "hit_3": hits["hit_3"],
                "hit_5": hits["hit_5"],
                "mrr": mrr,
                "top_3_retrieved": retrieved_names[:3]
            })

    # Agregação das métricas
    num_normal = len(metrics_records)
    agg_metrics = {
        "model": model_name,
        "hit_1": np.mean([m["hit_1"] for m in metrics_records]) if num_normal > 0 else 0.0,
        "hit_3": np.mean([m["hit_3"] for m in metrics_records]) if num_normal > 0 else 0.0,
        "hit_5": np.mean([m["hit_5"] for m in metrics_records]) if num_normal > 0 else 0.0,
        "recall_5": np.mean([m["recall_5"] for m in metrics_records]) if num_normal > 0 else 0.0,
        "mrr": np.mean([m["mrr"] for m in metrics_records]) if num_normal > 0 else 0.0,
        "rejection_rate": (rejected_out_of_scope_count / total_out_of_scope) if total_out_of_scope > 0 else 0.0,
        "p50_latency": np.percentile(latencies, 50) if latencies else 0.0,
        "p95_latency": np.percentile(latencies, 95) if latencies else 0.0,
        "avg_out_of_scope_score": np.mean(out_of_scope_scores) if out_of_scope_scores else 0.0,
        "avg_normal_score": np.mean(normal_scores) if normal_scores else 0.0
    }

    return {
        "summary": agg_metrics,
        "details": query_details
    }


def main():
    parser = argparse.ArgumentParser(
        description="Executa a avaliação do motor de busca semântica.")
    parser.add_argument(
        "--model",
        action="append",
        default=[],
        help="Nome do modelo do sentence-transformers (pode ser passado múltiplas vezes)."
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.2,
        help="Pontuação mínima (min_score) para calcular a taxa de rejeição de armadilhas."
    )
    parser.add_argument(
        "--queries",
        type=str,
        default="eval/queries.json",
        help="Caminho para o arquivo JSON de consultas."
    )
    args = parser.parse_args()

    # Se nenhum modelo foi passado via CLI, usa o padrão do settings
    models_to_eval = args.model if args.model else [settings.EMBEDDING_MODEL]

    os.makedirs("eval", exist_ok=True)

    all_summaries = []
    all_details = {}

    for model_name in models_to_eval:
        result = run_evaluation(
            model_name=model_name, min_score=args.min_score, queries_path=args.queries)
        if result:
            all_summaries.append(result["summary"])
            all_details[model_name] = result["details"]

    csv_path = "eval/results.csv"
    with open(csv_path, 'w', encoding='utf-8') as f:
        headers = ["model", "hit_1", "hit_3", "hit_5", "recall_5",
                   "mrr", "rejection_rate", "p50_latency", "p95_latency"]
        f.write(",".join(headers) + "\n")
        for s in all_summaries:
            row = [str(s[h]) for h in headers]
            f.write(",".join(row) + "\n")
    print(f"\nResultados consolidados salvos em {csv_path}")

    details_csv_path = "eval/results_by_query.csv"
    with open(details_csv_path, 'w', encoding='utf-8') as f:
        f.write(
            "model,id,query,type,hit_1,mrr,best_score,rejected_correctly,top_3_retrieved\n")
        for model_name, details in all_details.items():
            for d in details:
                top_3_str = " | ".join(d.get("top_3_retrieved", []))
                f.write(f"{model_name},{d.get('id')},\"{d.get('query')}\",{d.get('type')},{d.get('hit_1', '')},{d.get('mrr', '')},{d.get('best_score', '')},{d.get('rejected_correctly', '')},\"{top_3_str}\"\n")
    print(f"Detalhes por consulta salvos em {details_csv_path}")

    md_path = "eval/results.md"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("### Avaliação de Desempenho da Busca Semântica\n\n")
        f.write(
            "| Modelo | Hit@1 | Hit@3 | Hit@5 | Recall@5 | MRR | Rejeição Correta | p50 (ms) | p95 (ms) |\n")
        f.write(
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        for s in all_summaries:
            f.write(
                f"| `{s['model']}` | "
                f"{s['hit_1']:.2f} | "
                f"{s['hit_3']:.2f} | "
                f"{s['hit_5']:.2f} | "
                f"{s['recall_5']:.2f} | "
                f"{s['mrr']:.2f} | "
                f"{s['rejection_rate'] * 100:.1f}% | "
                f"{s['p50_latency']:.2f} | "
                f"{s['p95_latency']:.2f} |\n"
            )
        f.write("\n> *Critério de Relevância*: Considera-se relevante quando os ingredientes e o tipo de prato batem com a intenção da consulta.\n")
    print(f"Tabela em Markdown salva em {md_path}")
    print("\nAvaliação concluída com sucesso!")


if __name__ == "__main__":
    main()
