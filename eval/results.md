### Avaliação de Desempenho da Busca Semântica

| Modelo | Hit@1 | Hit@3 | Hit@5 | Recall@5 | MRR | Rejeição Correta | p50 (ms) | p95 (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `sentence-transformers/all-MiniLM-L6-v2` | 0.48 | 0.64 | 0.64 | 0.64 | 0.55 | 80.0% | 38.06 | 88.58 |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | 0.36 | 0.52 | 0.64 | 0.64 | 0.46 | 40.0% | 93.41 | 156.20 |

> *Critério de Relevância*: Considera-se relevante quando os ingredientes e o tipo de prato batem com a intenção da consulta.
