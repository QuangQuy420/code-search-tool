"use client";

interface RepoSelectorProps {
  repos: string[];
  selected: string;
  onChange: (repo: string) => void;
}

export default function RepoSelector({ repos, selected, onChange }: RepoSelectorProps) {
  if (repos.length === 0) return null;

  return (
    <select
      value={selected}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-700 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300"
    >
      <option value="">All repositories</option>
      {repos.map((repo) => (
        <option key={repo} value={repo}>
          {repo}
        </option>
      ))}
    </select>
  );
}
