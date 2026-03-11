export interface SearchResult {
  score: number;
  file_path: string;
  function_name: string;
  language: string;
  start_line: number;
  end_line: number;
  code: string;
  chunk_type: "function" | "class" | "method";
  repo_name: string;
}

export interface SearchResponse {
  results: SearchResult[];
  query: string;
  total: number;
}
