"use client";
import { useState, type ReactNode } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { ArrowLeft, RotateCcw, UserRound } from "lucide-react";
import { api, errorMessage, type DemoConfig } from "@/lib/partpilot";

export const primary = "inline-flex items-center justify-center rounded-xl bg-[#0F274A] px-5 py-3 text-sm font-semibold text-white shadow-2xs hover:bg-[#152e55] transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer";
export const secondary = "inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-medium hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer";
export const accent = "inline-flex items-center justify-center gap-2 rounded-xl bg-[#F5C767] px-5 py-3 text-sm font-semibold text-gray-900 shadow-2xs hover:bg-[#EEBA52] disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer";
export const field = "mt-2 w-full rounded-xl border border-slate-300 bg-white p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700";
export const card = "rounded-2xl border border-slate-200 bg-white p-5 sm:p-7 shadow-xs";

export function ErrorNotice({ message }: { message: string }) {
  return message ? <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{message}</div> : null;
}
export function DemoShell({ title, children, config, compact = false, decision = false, titleAction }: { title: string; children: ReactNode; config?: DemoConfig | null; compact?: boolean; decision?: boolean; titleAction?: ReactNode }) {
  const pathname = usePathname();
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
  return <div className="min-h-screen bg-[#F1F3F6] text-gray-800 font-sans">
    <header className="sticky top-0 z-40 border-b border-gray-200 bg-white"><div className={`mx-auto flex ${compact || decision ? "max-w-6xl" : "max-w-7xl"} min-h-16 flex-wrap items-center justify-between gap-4 px-4 sm:px-6 py-3`}>
      <Link href="/"><Image src="/logo.png" alt="PartPilot" width={130} height={46} className="h-8 w-auto" /></Link>
      <nav aria-label="Menu utama" className="flex flex-wrap items-center gap-2 text-sm">{[{ href: "/technician/", name: "Work order" }, { href: "/manager/", name: "Meja manajer" }].map(item => <Link key={item.href} href={item.href} aria-current={pathname.startsWith(item.href.slice(0, -1)) ? "page" : undefined} className={`rounded-lg px-3 py-2 font-semibold transition-colors ${pathname.startsWith(item.href.slice(0, -1)) ? "bg-blue-50 text-[#0F274A]" : "text-gray-500 hover:bg-gray-50 hover:text-[#0F274A]"}`}>{item.name}</Link>)}
        <button className={secondary} disabled={!config || busy} onClick={() => { setOpen(true); setError(""); setConfirmation(""); }}><RotateCcw size={15} className="mr-2" />Reset demo</button>
        <span aria-hidden="true" className="hidden h-9 w-9 items-center justify-center rounded-full border border-[#BAE6FD] bg-[#E0F2FE] text-[#0284C7] sm:flex"><UserRound size={19} /></span></nav>
    </div></header>
    <div className="border-b border-blue-100 bg-blue-50/70 px-5 py-2 text-center text-xs text-[#17375E]">DEMO • Stok sintetis • Vendor otomatis dihubungi melalui WhatsApp saat stok asal kurang • Keputusan tidak mengeksekusi pembelian</div>
    <main className={`mx-auto ${compact ? "max-w-5xl" : decision ? "max-w-6xl" : "max-w-7xl"} space-y-5 px-4 sm:px-6 py-6 sm:py-8`}><div className="flex flex-wrap items-center justify-between gap-4"><div><h1 className="text-xl sm:text-2xl font-bold uppercase tracking-tight text-[#0F274A]">{title}</h1><p className="mt-0.5 text-xs sm:text-sm text-gray-500"><Link href="/" className="hover:underline">Home</Link><span className="mx-1.5 text-gray-400">&gt;</span>{title}</p></div>{titleAction || ((compact || decision) && <Link href={decision ? "/manager/" : "/"} className={accent}><ArrowLeft size={16} />Kembali</Link>)}</div>{children}</main>
    {open && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-5"><section role="dialog" aria-modal="true" aria-labelledby="reset-heading" className={`${card} w-full max-w-lg space-y-4`}>
      <h2 id="reset-heading" className="text-xl font-bold">Kembalikan demo ke awal?</h2>
      <p className="text-sm text-slate-600">Riwayat WO, penawaran, dan pilihan demo aktif akan dibersihkan untuk semua pengguna demo. Stok sintetis dikembalikan ke kondisi awal. Data di luar database demo tidak disentuh.</p>
      <p className="text-sm text-slate-600">Percakapan WhatsApp aktif akan ditutup dan pesan yang belum dikirim dibatalkan. Pesan yang sudah terkirim serta catatan audit tetap disimpan. Reset tidak menarik kembali pesan dari ponsel vendor.</p>
      <label className="block text-sm font-medium">Ketik RESET DEMO<input autoFocus value={confirmation} onChange={e => setConfirmation(e.target.value)} className={field} disabled={busy} /></label>
      <ErrorNotice message={error} />
      <div className="flex justify-end gap-3"><button className={secondary} onClick={() => setOpen(false)} disabled={busy}>Batal</button><button className={primary} onClick={reset} disabled={busy || confirmation !== "RESET DEMO"}>{busy ? "Mereset…" : "Reset database demo"}</button></div>
    </section></div>}
  </div>;
}
