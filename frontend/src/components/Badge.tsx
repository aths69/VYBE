import type { ReactNode } from "react";

type Kind = "measured" | "calculated" | "estimated" | "warning" | "info";

// Section 2: measured/calculated/estimated must be visually distinguished
// everywhere they appear in the UI, not just documented in text.
export function Badge({ kind, children }: { kind: Kind; children: ReactNode }) {
  return <span className={`badge badge-${kind}`}>{children}</span>;
}
