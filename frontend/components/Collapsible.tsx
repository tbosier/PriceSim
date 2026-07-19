"use client";

import { useState } from "react";

interface CollapsibleProps {
  title: string;
  subtitle?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

export function Collapsible({
  title,
  subtitle,
  defaultOpen = false,
  children,
}: CollapsibleProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className="card overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition-colors hover:bg-white/[0.03]"
      >
        <span>
          <span className="block text-base font-semibold text-ink-50">
            {title}
          </span>
          {subtitle ? (
            <span className="mt-0.5 block text-sm text-ink-400">{subtitle}</span>
          ) : null}
        </span>
        <span
          className={`shrink-0 text-ink-400 transition-transform duration-200 ${
            open ? "rotate-180" : ""
          }`}
          aria-hidden
        >
          <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
            <path
              d="M5 8l5 5 5-5"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
      </button>
      {open ? (
        <div className="border-t border-white/[0.06] px-5 py-5 text-sm leading-relaxed text-ink-200">
          {children}
        </div>
      ) : null}
    </section>
  );
}
