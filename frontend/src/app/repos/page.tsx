"use client";

import { useState, useEffect, FormEvent } from "react";
import Link from "next/link";
import { indexRepo, listRepos, RepoInfo } from "@/lib/api";

const GITHUB_URL_RE = /^https:\/\/github\.com\/[\w.\-]+\/[\w.\-]+\/?$/;

export default function ReposPage() {
  const [repos, setRepos] = useState<RepoInfo[]>([]);
  const [repoUrl, setRepoUrl] = useState("");
  const [isIndexing, setIsIndexing] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const fetchRepos = () => {
    listRepos()
      .then(setRepos)
      .catch(() => {});
  };

  useEffect(() => {
    fetchRepos();
  }, []);

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    const url = repoUrl.trim();
    if (!GITHUB_URL_RE.test(url)) {
      setValidationError("Please enter a valid GitHub URL (https://github.com/owner/repo)");
      return;
    }

    setIsIndexing(true);
    setToast(null);
    try {
      const result = await indexRepo(url);
      setToast({
        type: "success",
        message: `Indexed ${result.repo_name}: ${result.chunks_parsed} chunks from ${result.files_found} files`,
      });
      setRepoUrl("");
      fetchRepos();
    } catch (err) {
      setToast({
        type: "error",
        message: err instanceof Error ? err.message : "Indexing failed",
      });
    } finally {
      setIsIndexing(false);
    }
  };

  const handleReindex = async (repoName: string) => {
    const url = `https://github.com/${repoName}`;
    setRepoUrl(url);
    setIsIndexing(true);
    setToast(null);
    try {
      const result = await indexRepo(url);
      setToast({
        type: "success",
        message: `Re-indexed ${result.repo_name}: ${result.chunks_parsed} chunks`,
      });
      setRepoUrl("");
      fetchRepos();
    } catch (err) {
      setToast({
        type: "error",
        message: err instanceof Error ? err.message : "Re-indexing failed",
      });
    } finally {
      setIsIndexing(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center bg-zinc-50 px-4 py-16 dark:bg-zinc-950">
      <header className="mb-12 text-center">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
          Manage Repositories
        </h1>
        <p className="mt-2 text-zinc-500 dark:text-zinc-400">
          Index GitHub repos for semantic code search
        </p>
        <Link
          href="/"
          className="mt-3 inline-block text-sm text-blue-600 hover:underline dark:text-blue-400"
        >
          Back to Search
        </Link>
      </header>

      {/* Toast */}
      {toast && (
        <div
          className={`mb-6 w-full max-w-2xl rounded-lg border p-4 text-sm ${
            toast.type === "success"
              ? "border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-300"
              : "border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300"
          }`}
        >
          {toast.message}
        </div>
      )}

      {/* Index form */}
      <form onSubmit={handleSubmit} className="w-full max-w-2xl">
        <div className="flex gap-2">
          <input
            type="text"
            value={repoUrl}
            onChange={(e) => {
              setRepoUrl(e.target.value);
              setValidationError(null);
            }}
            placeholder="https://github.com/owner/repo"
            className="flex-1 rounded-lg border border-zinc-300 bg-white px-4 py-3 text-base text-zinc-900 placeholder-zinc-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:placeholder-zinc-500"
            disabled={isIndexing}
          />
          <button
            type="submit"
            disabled={isIndexing || !repoUrl.trim()}
            className="rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isIndexing ? "Indexing..." : "Index Repository"}
          </button>
        </div>
        {validationError && (
          <p className="mt-2 text-sm text-red-500">{validationError}</p>
        )}
      </form>

      {/* Loading indicator */}
      {isIndexing && (
        <div className="mt-6 flex items-center gap-2 text-sm text-zinc-500">
          <svg
            className="h-5 w-5 animate-spin text-blue-600"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Indexing repository — this may take a minute...
        </div>
      )}

      {/* Repos list */}
      <div className="mt-10 w-full max-w-2xl">
        <h2 className="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
          Indexed Repositories
        </h2>
        {repos.length === 0 ? (
          <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-8 text-center dark:border-zinc-700 dark:bg-zinc-900">
            <p className="text-zinc-500 dark:text-zinc-400">
              No repositories indexed yet. Add one above to get started.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {repos.map((repo) => (
              <div
                key={repo.repo_name}
                className="flex items-center justify-between rounded-lg border border-zinc-200 bg-white px-4 py-3 shadow-sm dark:border-zinc-700 dark:bg-zinc-900"
              >
                <div>
                  <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                    {repo.repo_name}
                  </p>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">
                    {repo.vector_count} chunks indexed
                  </p>
                </div>
                <button
                  onClick={() => handleReindex(repo.repo_name)}
                  disabled={isIndexing}
                  className="rounded-md border border-zinc-300 px-3 py-1 text-xs font-medium text-zinc-600 transition-colors hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-600 dark:text-zinc-400 dark:hover:bg-zinc-800"
                >
                  Re-index
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
