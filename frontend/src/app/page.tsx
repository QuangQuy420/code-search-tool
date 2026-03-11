"use client";

import { useState } from "react";
import SearchBar from "@/components/SearchBar";
import ResultsList from "@/components/ResultsList";
import RepoSelector from "@/components/RepoSelector";
import { SearchResult } from "@/types/search";

export default function Home() {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [repos] = useState<string[]>([]);
  const [selectedRepo, setSelectedRepo] = useState("");

  const handleSearch = async (query: string) => {
    setIsLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      // TODO: Replace with actual API call (PER-15)
      await new Promise((resolve) => setTimeout(resolve, 500));
      setResults([]);
    } catch {
      setError("Failed to search. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleExplain = (result: SearchResult) => {
    // TODO: Implement SSE explanation (PER-16)
    console.log("Explain:", result.function_name);
  };

  return (
    <div className="flex min-h-screen flex-col items-center bg-zinc-50 px-4 py-16 dark:bg-zinc-950">
      <header className="mb-12 text-center">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
          Code Search
        </h1>
        <p className="mt-2 text-zinc-500 dark:text-zinc-400">
          Search code using natural language
        </p>
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
        />
      </div>
    </div>
  );
}
