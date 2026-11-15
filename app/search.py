import json
import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from .config import settings


class DocumentVectorSearch:
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        print(f"Carregando modelo de embeddings: {self.model_name}...")
        self.model = SentenceTransformer(self.model_name)
        self.index = None
        self.documents = []

    def load_documents(self, file_path: str):
        """Carrega o arquivo JSON com os pratos limpos."""
        print(f"Lendo dados preparados do arquivo: {file_path}...")
        self.documents = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for linha in f:
                if linha.strip():
                    self.documents.append(json.loads(linha))
        print(f"{len(self.documents)} pratos carregados com sucesso!")

    def process_documents(self):
        """Gera embeddings normalizados e cria o índice FAISS com IndexFlatIP (Produto Interno = Cosseno)."""
        print("Gerando vetores matemáticos normalizados (Embeddings)...")
        textos = [doc["text_for_embedding"] for doc in self.documents]

        # normalize_embeddings=True faz o produto interno (IndexFlatIP) equivaler à Similaridade de Cosseno
        embeddings = self.model.encode(
            textos, convert_to_numpy=True, normalize_embeddings=True
        ).astype('float32')

        dimensao = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimensao)
        self.index.add(embeddings)
        print("FAISS indexado com IndexFlatIP!")

    def save_index(self, index_path: str, metadata_path: str):
        """Salva o índice FAISS e os documentos em disco."""
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        faiss.write_index(self.index, index_path)
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)
        print(
            f"Índice salvo em {index_path} e metadados salvos em {metadata_path}.")

    def load_index(self, index_path: str, metadata_path: str) -> bool:
        """Carrega o índice FAISS e os metadados diretamente do disco se existirem."""
        if os.path.exists(index_path) and os.path.exists(metadata_path):
            print(f"Carregando índice FAISS do disco: {index_path}...")
            self.index = faiss.read_index(index_path)
            with open(metadata_path, 'r', encoding='utf-8') as f:
                self.documents = json.load(f)
            print(
                f"Índice e {len(self.documents)} metadados carregados com sucesso do disco!")
            return True
        return False

    def query(self, question: str, num_results: int = 3, min_score: float = 0.0):
        """Transforma o texto em vetor normalizado, busca os similares e aplica filtro de min_score."""
        vetor_pergunta = self.model.encode(
            [question], convert_to_numpy=True, normalize_embeddings=True
        ).astype('float32')

        # Busca um pouco a mais para garantir que teremos itens suficientes após o filtro de min_score
        k_busca = max(num_results * 2, 10)
        k_busca = min(k_busca, len(self.documents)
                      ) if self.documents else num_results

        scores, indices = self.index.search(vetor_pergunta, k_busca)

        resultados = []
        for i in range(len(indices[0])):
            posicao_no_dataset = indices[0][i]
            if posicao_no_dataset == -1:
                continue

            score = float(scores[0][i])

            # Aplica o filtro de min_score
            if score < min_score:
                continue

            prato = dict(self.documents[posicao_no_dataset])
            prato["score"] = round(score, 4)  # Similaridade entre 0 e 1
            resultados.append(prato)

            if len(resultados) >= num_results:
                break

        return resultados
