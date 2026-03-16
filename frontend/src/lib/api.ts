import { SearchResult } from "@/types/search";
import { logger } from "@/lib/logger";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const method = options?.method || 'GET';
  const startTime = performance.now();
  const requestId = `req-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  logger.info("API request", {
    method,
    endpoint: path,
    request_id: requestId,
  });

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (err) {
    const duration = performance.now() - startTime;
    logger.error("API error", {
      endpoint: path,
      error: err instanceof Error ? err.message : 'Unknown error',
      duration_ms: Math.round(duration),
      request_id: requestId,
    });
    throw new ApiError(
      "Backend is starting up, please wait...",
      0,
    );
  }

  const duration = performance.now() - startTime;
  const responseRequestId = res.headers.get('X-Request-ID');

  if (!res.ok) {
    if (res.status === 503) {
      logger.error("API error", {
        endpoint: path,
        status: res.status,
        duration_ms: Math.round(duration),
        request_id: responseRequestId || requestId,
      });
      throw new ApiError("Service temporarily unavailable", 503);
    }
    const body = await res.json().catch(() => ({}));
    logger.error("API error", {
      endpoint: path,
      status: res.status,
      error: body.detail || `Request failed (${res.status})`,
      duration_ms: Math.round(duration),
      request_id: responseRequestId || requestId,
    });
    throw new ApiError(
      body.detail || `Request failed (${res.status})`,
      res.status,
    );
  }

  logger.info("API response", {
    endpoint: path,
    status: res.status,
    duration_ms: Math.round(duration),
    request_id: responseRequestId || requestId,
  });

  return res.json();
}

export async function searchCode(
  query: string,
  topK: number = 5,
  repoName?: string,
): Promise<SearchResult[]> {
  const body: Record<string, unknown> = { query, top_k: topK };
  if (repoName) body.repo_name = repoName;

  const data = await request<{ results: SearchResult[] }>("/api/search", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return data.results;
}

export interface RepoInfo {
  repo_name: string;
  vector_count: number;
}

export async function listRepos(): Promise<RepoInfo[]> {
  const data = await request<{ repos: RepoInfo[] }>("/api/repos");
  return data.repos;
}

export async function indexRepo(
  repoUrl: string,
): Promise<{
  repo_name: string;
  files_found: number;
  chunks_parsed: number;
  vectors_stored: number;
}> {
  return request("/api/index", {
    method: "POST",
    body: JSON.stringify({ repo_url: repoUrl }),
  });
}

export function streamExplanation(
  code: string,
  language: string,
  functionName: string,
  onToken: (token: string) => void,
  onError: (error: string) => void,
  onDone: () => void,
): AbortController {
  const controller = new AbortController();
  const startTime = performance.now();
  const requestId = `explain-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  logger.info("Explain request", {
    function_name: functionName,
    language,
    request_id: requestId,
  });

  fetch(`${API_URL}/api/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, language, function_name: functionName }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok || !res.body) {
        const duration = performance.now() - startTime;
        logger.error("Explain error", {
          function_name: functionName,
          status: res.status,
          error: "Failed to start explanation",
          duration_ms: Math.round(duration),
          request_id: requestId,
        });
        onError("Failed to start explanation");
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data:")) {
            const data = line.slice(5).trim();
            if (data) onToken(data);
          } else if (line.startsWith("event:error")) {
            // Next data line will have the error message
          }
        }
      }
      const duration = performance.now() - startTime;
      logger.info("Explain complete", {
        function_name: functionName,
        duration_ms: Math.round(duration),
        request_id: requestId,
      });
      onDone();
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        const duration = performance.now() - startTime;
        const errorMsg = err.message?.includes("rate limit")
          ? "Explanation service is busy, try again in a moment"
          : "Network error — please retry";
        logger.error("Explain error", {
          function_name: functionName,
          error: err.message || 'Unknown error',
          duration_ms: Math.round(duration),
          request_id: requestId,
        });
        onError(errorMsg);
      }
    });

  return controller;
}

export { ApiError };
