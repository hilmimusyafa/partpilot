"use client";
import { useState, type ReactNode } from "react";
import Link from "next/link";
import Image from "next/image";
import { RotateCcw } from "lucide-react";
import { api, errorMessage, type DemoConfig } from "@/lib/partpilot";

export const primary = "inline-flex items-center justify-center rounded-xl bg-[#F5C767] px-5 py-3 text-sm font-semibold text-[#0F274A] hover:bg-[#eeba52] disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer";
export const secondary = "inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-medium hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer";
export const field = "mt-2 w-full rounded-xl border border-slate-300 bg-white p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700";
export const card = "rounded-2xl border border-slate-200 bg-white p-5 sm:p-7 shadow-xs";

export function ErrorNotice({ message }: { message: string }) {
  return message ? <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{message}</div> : null;
}
export function DemoShell({ title, children, config }: { title: string; children: ReactNode; config?: DemoConfig | null }) {
  const [open, setOpen] = useState(false);
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function reset() {
    if (!config || busy || confirmation !== "RESET DEMO") return;
    setBusy(true); setError("");
    try {
      await api("/demo/reset", { confirmation, expected_generation: config.generation }, `reset-${config.generation}`);
      try { for (const key of ["partpilot_technician_draft", "partpilot_orders"]) localStorage.removeItem(key); } catch { /* Storage may be disabled; server reset already succeeded. */ }
      // A reset must discard all client state and prefetched workflow pages.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.assign("/manager/");
    } catch (e) { setError(errorMessage(e)); setBusy(false); }
  }
  return <div className="min-h-screen bg-[#F1F3F6] text-[#0F274A]">
    <header className="border-b border-slate-200 bg-white"><div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-5 py-4">
      <Link href="/"><Image src="/logo.png" alt="PartPilot" width={130} height={46} className="h-8 w-auto" /></Link>
      <nav aria-label="Menu utama" className="flex flex-wrap items-center gap-3 text-sm"><Link href="/technician/" className="hover:underline">Work order</Link><Link href="/manager/" className="hover:underline">Meja manajer</Link>
        <button className={secondary} disabled={!config || busy} onClick={() => { setOpen(true); setError(""); setConfirmation(""); }}><RotateCcw size={15} className="mr-2" />Reset demo</button>
      </nav>
    </div></header>
    <div className="border-b border-amber-200 bg-amber-50 px-5 py-2 text-center text-xs text-amber-900">DEMO • Data sintetis • WhatsApp simulator • Pilihan manajer tidak mengeksekusi pembelian atau mutasi</div>
    <main className="mx-auto max-w-7xl space-y-5 px-5 py-7"><h1 className="text-2xl font-bold">{title}</h1>{children}</main>
    {open && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-5"><section role="dialog" aria-modal="true" aria-labelledby="reset-heading" className={`${card} w-full max-w-lg space-y-4`}>
      <h2 id="reset-heading" className="text-xl font-bold">Kembalikan demo ke awal?</h2>
      <p className="text-sm text-slate-600">Riwayat WO, penawaran, dan pilihan demo aktif akan dibersihkan untuk semua pengguna demo. Stok sintetis dikembalikan ke kondisi awal. Data di luar database demo tidak disentuh.</p>
      <label className="block text-sm font-medium">Ketik RESET DEMO<input autoFocus value={confirmation} onChange={e => setConfirmation(e.target.value)} className={field} disabled={busy} /></label>
      <ErrorNotice message={error} />
      <div className="flex justify-end gap-3"><button className={secondary} onClick={() => setOpen(false)} disabled={busy}>Batal</button><button className={primary} onClick={reset} disabled={busy || confirmation !== "RESET DEMO"}>{busy ? "Mereset…" : "Reset database demo"}</button></div>
    </section></div>}
  </div>;
}
