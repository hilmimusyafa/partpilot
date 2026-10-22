"use client";
import { useEffect, useEffectEvent, useRef, useState, type Dispatch, type SetStateAction } from "react";
import { api, errorMessage, type Comparison, type Option, type Run, type WhatsAppConversation, type WhatsAppConversations } from "@/lib/partpilot";

type LiveState = {
  run: Run | null; comparison: Comparison | null; selected: string; confirm: Option | null; busy: boolean;
  setRun: Dispatch<SetStateAction<Run | null>>; setComparison: Dispatch<SetStateAction<Comparison | null>>;
  setSelected: Dispatch<SetStateAction<string>>; setConversations: Dispatch<SetStateAction<WhatsAppConversation[]>>;
  refresh: number;
};

export function useLiveComparison(state: LiveState) {
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const requestInFlight = useRef(false);
  const readState = useEffectEvent(() => state);
  const liveRunId = state.run?.transport === "whatsapp" ? state.run.id : null;
  const refresh = state.refresh;

  useEffect(() => {
    if (!liveRunId) return;
    const runId = liveRunId;
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try {
        // Conversation failures must not prevent fresh quotes from reaching the table.
        const [runResult, chatResult] = await Promise.allSettled([
          api<Run>(`/demo/sourcing-runs/${runId}`), api<WhatsAppConversations>("/whatsapp/conversations"),
        ]);
        if (!active) return;
        const current = readState();
        if (chatResult.status === "fulfilled") current.setConversations(chatResult.value.conversations.filter(chat => chat.run_id === runId));
        if (runResult.status === "rejected") throw runResult.reason;
        const next = runResult.value;
        current.setRun(previous => previous?.id === next.id && previous.version > next.version ? previous : next);
        if (next.decision) current.setSelected(next.decision.option_id);
        if (current.selected || next.decision) { setError(""); return; }
        if (current.busy || current.confirm || requestInFlight.current) return;
        requestInFlight.current = true;
        try {
          let result: Comparison;
          if (!current.comparison || current.comparison.source_run_version !== next.version) {
            setRefreshing(true);
            result = await api<Comparison>(`/demo/sourcing-runs/${runId}/prepare-comparison`, {}, `comparison-${runId}-${next.version}`);
          } else {
            // Re-read validity without creating another comparison for an unchanged run.
            result = await api<Comparison>(`/demo/comparisons/${current.comparison.id}`);
          }
          if (!Number.isInteger(result.source_run_version)) throw new Error("Versi penawaran pada perbandingan belum tersedia.");
          if (!active) return;
          const latest = readState();
          if (!latest.selected && !latest.confirm && !latest.busy && latest.run?.id === runId
            && latest.run.version <= result.source_run_version) latest.setComparison(result);
          setError(chatResult.status === "rejected" ? "Percakapan belum dapat dimuat. Perbandingan tetap diperbarui; sistem akan mencoba lagi." : "");
        } finally {
          requestInFlight.current = false;
          if (active) setRefreshing(false);
        }
      } catch (failure) {
        if (active) setError(`Pembaruan otomatis tertunda: ${errorMessage(failure)} Sistem akan mencoba lagi.`);
      } finally {
        if (active) timer = setTimeout(poll, 5000);
      }
    }
    void poll();
    return () => { active = false; clearTimeout(timer); };
  }, [liveRunId, refresh]);
  return { refreshing, error };
}
