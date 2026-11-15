export interface DishItem {
    dish_name: string;
    score: number;
    [key: string]: any;
  }
  
  export interface SearchResponse {
    query: string;
    model: string;
    latency_ms: number;
    message: string;
    results: DishItem[];
  }