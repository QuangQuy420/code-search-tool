"use client";

import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { SearchResult } from "@/types/search";

const LANGUAGE_COLORS: Record<string, string> = {
  python: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  javascript: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  typescript: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  java: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  go: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200",
  rust: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
};

interface ResultCardProps {
  result: SearchResult;
  onExplain: (result: SearchResult) => void;
}

export default function ResultCard({ result, onExplain }: ResultCardProps) {
  const [expanded, setExpanded] = useState(true);
  const scorePercent = Math.round(result.score * 100);
  const langColor =
    LANGUAGE_COLORS[result.language.toLowerCase()] ??
    "bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200";

  return (
    <div className="overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-sm transition-shadow hover:shadow-md dark:border-zinc-700 dark:bg-zinc-900">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-100 px-4 py-3 dark:border-zinc-800">
        <div className="flex items-center gap-2 overflow-hidden">
          <button
            onClick={() => setExpanded(!expanded)}
            className="shrink-0 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
          >
            <svg
              className={`h-4 w-4 transition-transform ${expanded ? "rotate-90" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
          <h3 className="truncate text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            {result.file_path}
            <span className="ml-1 font-normal text-zinc-500 dark:text-zinc-400">
              : {result.function_name}
            </span>
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${langColor}`}>
            {result.language}
          </span>
          <span className="text-xs text-zinc-500 dark:text-zinc-400">
            Lines {result.start_line}-{result.end_line}
          </span>
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              scorePercent >= 80
                ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                : scorePercent >= 60
                  ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
                  : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
            }`}
          >
            {scorePercent}%
          </span>
        </div>
      </div>

      {/* Code */}
      {expanded && (
        <div className="text-sm">
          <SyntaxHighlighter
            language={result.language.toLowerCase()}
            style={oneDark}
            showLineNumbers
            startingLineNumber={result.start_line}
            customStyle={{ margin: 0, borderRadius: 0 }}
          >
            {result.code}
          </SyntaxHighlighter>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between border-t border-zinc-100 px-4 py-2 dark:border-zinc-800">
        <span className="text-xs text-zinc-400">{result.chunk_type}</span>
        <button
          onClick={() => onExplain(result)}
          className="rounded-md bg-violet-600 px-3 py-1 text-xs font-medium text-white transition-colors hover:bg-violet-700"
        >
          Explain
        </button>
      </div>
    </div>
  );
}
