"use client";

import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { API_BASE_URL } from "@/lib/api";

export const DEFAULT_PHOTO_FALLBACK =
  "data:image/svg+xml," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800"><rect fill="#e5e7eb" width="1200" height="800"/><text x="600" y="400" dominant-baseline="middle" text-anchor="middle" fill="#6b7280" font-family="system-ui,sans-serif" font-size="32">Photo unavailable</text></svg>'
  );

function normalizeAssetUrl(url?: string): string {
  if (!url) return DEFAULT_PHOTO_FALLBACK;
  return url.replace(/^https?:\/\/(?:127\.0\.0\.1|localhost):\d+/i, API_BASE_URL);
}

export function InteractivePhoto({
  src,
  alt,
  className = "object-cover",
  sizes = "(max-width: 768px) 100vw, 33vw",
}: {
  src?: string;
  alt: string;
  className?: string;
  sizes?: string;
}) {
  const [open, setOpen] = useState(false);
  const [failed, setFailed] = useState(false);
  const normalized = useMemo(() => normalizeAssetUrl(src), [src]);
  const displaySrc = failed ? DEFAULT_PHOTO_FALLBACK : normalized;

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <button
        type="button"
        className="absolute inset-0 cursor-zoom-in"
        onClick={() => setOpen(true)}
        aria-label={`Open photo of ${alt}`}
      >
        <Image
          src={displaySrc}
          alt={alt}
          fill
          sizes={sizes}
          className={className}
          onError={() => setFailed(true)}
        />
      </button>

      {open && (
        <div
          className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => setOpen(false)}
        >
          <div
            className="relative w-[min(1200px,95vw)] h-[min(760px,85vh)]"
            onClick={(e) => e.stopPropagation()}
          >
            <Image
              src={displaySrc}
              alt={alt}
              fill
              sizes="95vw"
              className="object-contain"
            />
            <button
              type="button"
              className="absolute top-3 right-3 rounded-md bg-black/60 text-white px-3 py-1 text-sm"
              onClick={() => setOpen(false)}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </>
  );
}

