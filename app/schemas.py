from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Any


class RecomendacaoItem(BaseModel):
    dish_name: str = Field(..., description="Nome do prato")
    score: float = Field(...,
                         description="Pontuação de similaridade ou distância vetorial")

    class Config:
        extra = "allow"


class PedidoClienteSchema(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=300,
        description="Texto da busca ou pedido do cliente (entre 3 e 300 caracteres)"
    )
    top_k: int = Field(
        3,
        ge=1,
        le=10,
        description="Número máximo de resultados a retornar (de 1 a 10)"
    )
    min_score: Optional[float] = Field(
        None,
        description="Pontuação mínima opcional para filtragem"
    )

    @field_validator("query")
    @classmethod
    def validar_query_nao_vazia(cls, v: str) -> str:
        if not v.strip():
            raise ValueError(
                "A query não pode conter apenas espaços em branco.")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Quero um prato leve com frango e vegetais",
                "top_k": 3,
                "min_score": 0.0
            }
        }


class RespostaRecomendacaoSchema(BaseModel):
    query: str = Field(..., description="Query original enviada pelo cliente")
    model: str = Field(..., description="Modelo de embeddings utilizado")
    latency_ms: float = Field(...,
                              description="Tempo de processamento em milissegundos")
    results: List[Any] = Field(...,
                               description="Lista de pratos recomendados com score")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Quero um prato leve com frango e vegetais",
                "model": "all-MiniLM-L6-v2",
                "latency_ms": 45.2,
                "results": [
                    {
                        "dish_name": "Frango Grelhado com Salada",
                        "score": 0.35,
                        "Typical Price (USD)": 12.50,
                        "text_for_embedding": "Frango Grelhado com Salada e legumes frescos."
                    }
                ]
            }
        }
