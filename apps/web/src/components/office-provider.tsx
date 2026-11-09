"use client";
import { createContext, useContext, useState } from "react";
import { usePoll } from "@/lib/use-poll";
import type { OfficeStatus } from "@/lib/types";
type OfficeContext = ReturnType<typeof usePoll<OfficeStatus>> & { paused: boolean; setPaused: (paused: boolean) => void };
const Context = createContext<OfficeContext | null>(null);
export function OfficeProvider({ children }: { children: React.ReactNode }) {
  const [paused, setPaused] = useState(false);
  const status = usePoll<OfficeStatus>("/api/status", 4000, paused);
  return <Context.Provider value={{ ...status, paused, setPaused }}>{children}</Context.Provider>;
}
export function useOffice() {
  const value = useContext(Context);
  if (!value) throw new Error("OfficeProvider diperlukan.");
  return value;
}
