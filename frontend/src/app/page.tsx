"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import SearchBar from "@/components/SearchBar";
import ResultsList from "@/components/ResultsList";
import RepoSelector from "@/components/RepoSelector";
import { SearchResult } from "@/types/search";
import { searchCode, listRepos, streamExplanation } from "@/lib/api";
import Link from "next/link";

export default function Home() {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [repos, setRepos] = useState<string[]>([]);
  const [selectedRepo, setSelectedRepo] = useState("");

  // SSE explanation state
  const [explanations, setExplanations] = useState<Record<string, string>>({});
  const [explainingKey, setExplainingKey] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Debounce ref
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    listRepos()
      .then((r) => setRepos(r.map((repo) => repo.repo_name)))
      .catch(() => {});
  }, []);

  const handleSearch = useCallback(
    async (query: string) => {
      // Debounce 300ms
      if (debounceRef.current) clearTimeout(debounceRef.current);

      debounceRef.current = setTimeout(async () => {
        setIsLoading(true);
        setError(null);
        setHasSearched(true);
        setExplanations({});
        setExplainingKey(null);

        try {
          const data = await searchCode(
            query,
            5,
            selectedRepo || undefined,
          );
          setResults(data);
        } catch (err) {
          setError(
            err instanceof Error ? err.message : "Failed to search. Please try again.",
          );
          setResults([]);
        } finally {
          setIsLoading(false);
        }
      }, 300);
    },
    [selectedRepo],
  );

  const handleExplain = useCallback((result: SearchResult) => {
    const key = `${result.file_path}:${result.function_name}:${result.start_line}`;

    // Cancel any in-flight explanation
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }

    // Toggle off if already showing
    if (explainingKey === key) {
      setExplainingKey(null);
      return;
    }

    setExplainingKey(key);
    setExplanations((prev) => ({ ...prev, [key]: "" }));

    abortRef.current = streamExplanation(
      result.code,
      result.language,
      result.function_name,
      (token) => {
        setExplanations((prev) => ({
          ...prev,
          [key]: (prev[key] || "") + token,
        }));
      },
      (err) => {
        setExplanations((prev) => ({
          ...prev,
          [key]: `Error: ${err}`,
        }));
        setExplainingKey(null);
      },
      () => {
        setExplainingKey(null);
      },
    );
  }, [explainingKey]);

  return (
    <div className="flex min-h-screen flex-col items-center bg-zinc-50 px-4 py-16 dark:bg-zinc-950">
      <header className="mb-12 text-center">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
          Code Search
        </h1>
        <p className="mt-2 text-zinc-500 dark:text-zinc-400">
          Search code using natural language
        </p>
        <Link
          href="/repos"
          className="mt-3 inline-block text-sm text-blue-600 hover:underline dark:text-blue-400"
        >
          Manage Repositories
        </Link>
      </header>

      <div className="flex w-full max-w-2xl flex-col items-center gap-4">
        <SearchBar onSearch={handleSearch} isLoading={isLoading} />
        <RepoSelector repos={repos} selected={selectedRepo} onChange={setSelectedRepo} />
      </div>

      <div className="mt-8 w-full max-w-2xl">
        <ResultsList
          results={results}
          isLoading={isLoading}
          hasSearched={hasSearched}
          error={error}
          onExplain={handleExplain}
          explanations={explanations}
          explainingKey={explainingKey}
        />
      </div>
    </div>
  );
}
