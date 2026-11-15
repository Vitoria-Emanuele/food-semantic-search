from app.search import DocumentVectorSearch
from app.config import settings
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def main():
    print("Iniciando construção e persistência do índice vetorial...")
    buscador = DocumentVectorSearch(model_name=settings.EMBEDDING_MODEL)

    if not os.path.exists(settings.DATA_PATH):
        print(f"Erro: Arquivo de dados não encontrado em {settings.DATA_PATH}")
        return

    buscador.load_documents(settings.DATA_PATH)
    buscador.process_documents()
    buscador.save_index(settings.INDEX_PATH, settings.METADATA_PATH)
    print("Processo de build do índice concluído com sucesso!")


if __name__ == "__main__":
    main()
