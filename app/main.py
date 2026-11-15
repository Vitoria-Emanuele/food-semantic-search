from contextlib import asynccontextmanager
import time
import logging
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from .search import DocumentVectorSearch
from .config import settings
from .schemas import PedidoClienteSchema, RespostaRecomendacaoSchema

# Configuração básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Inicializando motor de IA...")
    buscador = DocumentVectorSearch()
    try:
        buscador.load_documents(settings.DATA_PATH)
        buscador.process_documents()
        logger.info("Sistema pronto para recomendações.")
    except Exception as e:
        logger.error(f"Erro crítico ao carregar dados: {e}")
        # Armazenamos None para indicar que falhou o carregamento
        app.state.buscador = None
        raise e

    app.state.buscador = buscador

    yield

    logger.info("Encerrando aplicação...")

# Instanciação da API com título, descrição e versão
app = FastAPI(
    title="API de Busca Semântica de Pratos de Rua",
    description="API inteligente baseada em RAG e FAISS para recomendação semântica de pratos culinários.",
    version="1.0.0",
    lifespan=lifespan
)

# Configuração do Middleware de CORS (Tarefa 6)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check(request: Request):
    """Endpoint de verificação de saúde da API e contagem de pratos indexados (Tarefa 4)."""
    buscador = getattr(request.app.state, "buscador", None)

    if not buscador or buscador.index is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="O índice de busca não está carregado ou a aplicação falhou na inicialização."
        )

    total_documents = len(buscador.documents)
    return {
        "status": "healthy",
        "indexed_documents": total_documents,
        "model": settings.EMBEDDING_MODEL
    }


@app.post("/sugerir-prato", response_model=RespostaRecomendacaoSchema)
async def sugerir_prato(request: Request, pedido: PedidoClienteSchema):
    start_time = time.time()

    # Validação de segurança: verifica se o índice foi carregado (Tarefa 5)
    buscador = getattr(request.app.state, "buscador", None)
    if not buscador or buscador.index is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço indisponível: o índice vetorial não foi carregado corretamente."
        )

    try:
        num_results = pedido.top_k if pedido.top_k else settings.TOP_K
        resultados_faiss = buscador.query(
            pedido.query, num_results=num_results)

        results_formatados = []
        for item in resultados_faiss:
            dish_name = item.get("Dish Name") or item.get(
                "dish_name") or "Prato Desconhecido"
            score_item = item.get("score", 0.0)

            item_copy = dict(item)
            item_copy["dish_name"] = dish_name
            item_copy["score"] = score_item
            results_formatados.append(item_copy)

        end_time = time.time()
        latency_ms = round((end_time - start_time) * 1000, 2)

        # Logging da consulta e do tempo de resposta (Tarefa 7)
        logger.info(
            f"Consulta: '{pedido.query}' | Latência: {latency_ms} ms | Resultados retornados: {len(results_formatados)}")

        return {
            "query": pedido.query,
            "model": settings.EMBEDDING_MODEL,
            "latency_ms": latency_ms,
            "results": results_formatados
        }
    except Exception as e:
        logger.error(f"Erro no processamento da busca: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro no processamento: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
