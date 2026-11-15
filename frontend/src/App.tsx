import { useRef, useState } from 'react';
import { searchDishes } from './api';
import './index.css';
import type { DishItem, SearchResponse } from './types';

export default function App() {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [history, setHistory] = useState<string[]>([]);
  
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleSearch = async (searchQuery: string) => {
    if (!searchQuery.trim()) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setLoading(true);
    setError(null);
    setQuery(searchQuery);

    try {
      const result = await searchDishes(searchQuery, topK, abortControllerRef.current.signal);
      setData(result);
      setHistory(prev => [searchQuery, ...prev.filter(h => h !== searchQuery)].slice(0, 5));
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setError('Não foi possível conectar ao servidor ou a API está offline.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <header>
        <h1>Street Food Semantic Search</h1>
        <p>Encontre pratos de rua do mundo todo usando Inteligência Artificial e FAISS.</p>
        <p><a href="https://github.com/vitoria/Project_AgentAI" target="_blank" rel="noreferrer">GitHub Repository</a></p>
      </header>

      <div className="search-box">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch(query)}
          placeholder="Ex: Quero um prato apimentado com frango..."
          aria-label="Campo de busca de pratos"
        />
        <select value={topK} onChange={(e) => setTopK(Number(e.target.value))} aria-label="Quantidade de resultados">
          <option value={3}>Top 3</option>
          <option value={5}>Top 5</option>
        </select>
        <button onClick={() => handleSearch(query)}>Buscar</button>
      </div>

      <div className="chips">
        <span style={{ alignSelf: 'center', fontSize: '0.85rem', color: 'var(--text-muted)' }}>Exemplos:</span>
        <button className="chip" onClick={() => handleSearch("spicy Mexican food with cheese and tortilla")}>
          Spicy Mexican Food
        </button>
        <button className="chip" onClick={() => handleSearch("something sweet with fruit and coconut")}>
          Sweet with Fruit & Coconut
        </button>
        <button className="chip" onClick={() => handleSearch("espetinho de frango grelhado")}>
          Espetinho de frango
        </button>
      </div>

      {history.length > 0 && (
        <div style={{ marginBottom: '1.5rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Buscas recentes: {history.map((h, i) => (
            <span key={i} style={{ cursor: 'pointer', margin: '0 0.4rem', textDecoration: 'underline' }} onClick={() => handleSearch(h)}>
              {h}
            </span>
          ))}
        </div>
      )}

      <main aria-live="polite">
        {loading && <p style={{ textAlign: 'center' }}>Carregando recomendações...</p>}

        {error && (
          <div className="card" style={{ borderColor: '#ef4444', textAlign: 'center' }}>
            <p style={{ color: '#ef4444' }}>{error}</p>
            <button className="chip" onClick={() => handleSearch(query)}>Tentar de novo</button>
          </div>
        )}

        {!loading && !error && data && (
          <div>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
              {data.message} ({data.latency_ms} ms)
            </p>

            {data.results.length === 0 ? (
              <div className="card" style={{ textAlign: 'center' }}>
                <p>Nenhum prato parecido encontrado para sua busca.</p>
              </div>
            ) : (
              data.results.map((dish: DishItem, index: number) => {
                const percent = Math.round(dish.score * 100);
                return (
                  <div key={index} className="card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <h3 style={{ margin: 0 }}>{dish.dish_name}</h3>
                      <span style={{ fontSize: '0.9rem', fontWeight: 'bold' }}>{percent}% Similaridade</span>
                    </div>
                    
                    <div className="similarity-bar-container">
                      <div className="similarity-bar" style={{ width: `${Math.max(percent, 5)}%` }}></div>
                    </div>

                    {dish['Typical Price (USD)'] && (
                      <p style={{ fontSize: '0.85rem', margin: '0.2rem 0' }}>
                        <strong>Preço Médio:</strong> ${dish['Typical Price (USD)']}
                      </p>
                    )}

                    {dish['text_for_embedding'] && (
                      <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                        {dish['text_for_embedding']}
                      </p>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}
      </main>

      <footer>
        <p>
          <a href="/docs" target="_blank" rel="noreferrer">Documentação da API (Swagger)</a> | <a href="https://github.com" target="_blank" rel="noreferrer">Repositório GitHub</a>
        </p>
      </footer>
    </div>
  );
}