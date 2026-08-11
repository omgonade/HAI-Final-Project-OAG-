"use client";

import { useEffect, useRef, useState } from "react";
import { displayOptionLabel } from "@/lib/fieldHelp";

export default function OptionSelect({
  value,
  options,
  optionHelp,
  onChange,
}: {
  value: string;
  options: string[];
  optionHelp?: Record<string, string>;
  onChange: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onEscape(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onEscape);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onEscape);
    };
  }, []);

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between gap-2 border rounded-lg px-3 py-2 text-left bg-white dark:bg-zinc-900 border-black/15 dark:border-white/20 hover:border-black/30 dark:hover:border-white/40 shadow-sm transition-colors"
      >
        <span className="truncate">{displayOptionLabel(value)}</span>
        <svg
          className={`w-4 h-4 shrink-0 text-black/40 dark:text-white/40 transition-transform ${open ? "rotate-180" : ""}`}
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {open && (
        <div className="absolute z-20 mt-1 w-full max-h-72 overflow-y-auto rounded-lg border border-black/15 dark:border-white/20 bg-white dark:bg-zinc-900 shadow-lg py-1">
          {options.map((opt) => {
            const selected = opt === value;
            const help = optionHelp?.[opt];
            return (
              <button
                key={opt}
                type="button"
                onClick={() => {
                  onChange(opt);
                  setOpen(false);
                }}
                className={`w-full flex items-start justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-black/5 dark:hover:bg-white/10 ${
                  selected ? "bg-blue-50 dark:bg-blue-950/50" : ""
                }`}
              >
                <span>
                  <span className={`block ${selected ? "font-medium" : ""}`}>
                    {displayOptionLabel(opt)}
                  </span>
                  {help && (
                    <span className="block text-xs text-black/50 dark:text-white/50 mt-0.5">
                      {help}
                    </span>
                  )}
                </span>
                {selected && (
                  <svg className="w-4 h-4 shrink-0 text-blue-600 dark:text-blue-400 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
