from contextlib import asynccontextmanager
import time
import logging
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from .search import DocumentVectorSearch
from .config import settings
from .schemas import PedidoClienteSchema, RespostaRecomendacaoSchema

from fastapi.staticfiles import StaticFiles
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Inicializando motor de busca semântica...")
    buscador = DocumentVectorSearch(model_name=settings.EMBEDDING_MODEL)
    try:
        carregado_do_disco = buscador.load_index(
            settings.INDEX_PATH, settings.METADATA_PATH)

        if not carregado_do_disco:
            logger.info(
                "Índice persistido não encontrado. Construindo a partir do dataset...")
            buscador.load_documents(settings.DATA_PATH)
            buscador.process_documents()
            buscador.save_index(settings.INDEX_PATH, settings.METADATA_PATH)

        logger.info("Sistema pronto para recomendações.")
    except Exception as e:
        logger.error(f"Erro crítico ao carregar dados ou índice: {e}")
        app.state.buscador = None
        raise e

    app.state.buscador = buscador

    yield

    logger.info("Encerrando aplicação...")

app = FastAPI(
    title="API de Busca Semântica de Pratos de Rua",
    description="API inteligente baseada em RAG, FAISS (Similaridade de Cosseno) e Pydantic.",
    version="2.0.0",
    lifespan=lifespan
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check(request: Request):
    buscador = getattr(request.app.state, "buscador", None)

    if not buscador or buscador.index is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="O índice de busca não está carregado ou a aplicação falhou na inicialização."
        )

    return {
        "status": "healthy",
        "indexed_documents": len(buscador.documents),
        "model": settings.EMBEDDING_MODEL
    }


@app.post("/sugerir-prato", response_model=RespostaRecomendacaoSchema)
async def sugerir_prato(request: Request, pedido: PedidoClienteSchema):
    start_time = time.time()

    buscador = getattr(request.app.state, "buscador", None)
    if not buscador or buscador.index is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço indisponível: o índice vetorial não foi carregado corretamente."
        )

    try:
        num_results = pedido.top_k if pedido.top_k else settings.TOP_K
        min_score = pedido.min_score if pedido.min_score is not None else settings.MIN_SCORE

        resultados_faiss = buscador.query(
            question=pedido.query,
            num_results=num_results,
            min_score=min_score
        )

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

        if not results_formatados:
            message = "Nenhum prato encontrado com o nível de similaridade desejado. Tente flexibilizar os termos ou o filtro mínimo."
        else:
            message = "Encontramos estas opções para você:"

        logger.info(
            f"Consulta: '{pedido.query}' | Latência: {latency_ms} ms | Resultados: {len(results_formatados)}")

        return {
            "query": pedido.query,
            "model": settings.EMBEDDING_MODEL,
            "latency_ms": latency_ms,
            "message": message,
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

frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")