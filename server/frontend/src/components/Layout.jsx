import React from "react";

export default function Layout({ children }) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="h-14 bg-white shadow flex items-center px-6">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-blue-600 text-white flex items-center justify-center text-xs font-bold">
            DS
          </div>
          <span className="font-semibold text-sm">
            Dataset Drift Studio
          </span>
          <span className="ml-2 text-xs text-gray-400">
            · SQLite + DVC Hybrid Demo
          </span>
        </div>
      </header>
      <main className="flex-1 p-4">{children}</main>
    </div>
  );
}