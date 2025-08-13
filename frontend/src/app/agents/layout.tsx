import * as React from "react";

export default function AgentsLayout({ children }: { children: React.ReactNode }) {
  // Simply pass through children - let the root layout handle the main structure
  return <>{children}</>;
}