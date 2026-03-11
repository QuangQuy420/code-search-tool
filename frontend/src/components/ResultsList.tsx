"use client";

import { SearchResult } from "@/types/search";
import ResultCard from "./ResultCard";

interface ResultsListProps {
  results: SearchResult[];
  isLoading: boolean;
  hasSearched: boolean;
  error: string | null;
  onExplain: (result: SearchResult) => void;
}

export default function ResultsList({
  results,
  isLoading,
  hasSearched,
  error,
  onExplain,
}: ResultsListProps) {
  if (error) {
    return (
      <div className="w-full max-w-2xl rounded-lg border border-red-200 bg-red-50 p-4 text-center text-sm text-red-600 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
        {error}
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex w-full max-w-2xl items-center justify-center py-12">
        <svg
          className="h-8 w-8 animate-spin text-blue-600"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
    );
  }

  if (hasSearched && results.length === 0) {
    return (
      <div className="w-full max-w-2xl rounded-lg border border-zinc-200 bg-zinc-50 p-8 text-center dark:border-zinc-700 dark:bg-zinc-900">
        <p className="text-zinc-500 dark:text-zinc-400">No results found. Try a different query.</p>
      </div>
    );
  }

  if (!hasSearched) return null;

  return (
    <div className="flex w-full max-w-2xl flex-col gap-4">
      <p className="text-sm text-zinc-500 dark:text-zinc-400">
        {results.length} result{results.length !== 1 ? "s" : ""} found
      </p>
      {results.map((result, i) => (
        <ResultCard key={`${result.file_path}-${result.function_name}-${i}`} result={result} onExplain={onExplain} />
      ))}
    </div>
  );
}
