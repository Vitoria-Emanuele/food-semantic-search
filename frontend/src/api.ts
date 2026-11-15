import type { SearchResponse } from "./types";


const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export async function searchDishes(
  query: string,
  topK: number,
  signal?: AbortSignal
): Promise<SearchResponse> {
  const response = await fetch(`${API_BASE_URL}/sugerir-prato`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      top_k: topK,
      min_score: 0.0,
    }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`Erro na API: ${response.statusText}`);
  }

  return response.json();
}