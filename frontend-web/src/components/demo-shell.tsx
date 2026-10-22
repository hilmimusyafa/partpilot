"use client";
import { type ReactNode } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { ArrowLeft, UserRound } from "lucide-react";
import { type DemoConfig } from "@/lib/partpilot";

export const primary = "inline-flex items-center justify-center rounded-xl bg-[#0F274A] px-5 py-3 text-sm font-semibold text-white shadow-2xs hover:bg-[#152e55] transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer";
export const secondary = "inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-medium hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer";
export const accent = "inline-flex items-center justify-center gap-2 rounded-xl bg-[#F5C767] px-5 py-3 text-sm font-semibold text-gray-900 shadow-2xs hover:bg-[#EEBA52] disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer";
export const field = "mt-2 w-full rounded-xl border border-slate-300 bg-white p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700";
export const card = "rounded-2xl border border-slate-200 bg-white p-5 sm:p-7 shadow-xs";

export function ErrorNotice({ message }: { message: string }) {
  return message ? <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{message}</div> : null;
}
export function DemoShell({ title, children, compact = false, decision = false, titleAction }: { title: string; children: ReactNode; config?: DemoConfig | null; compact?: boolean; decision?: boolean; titleAction?: ReactNode }) {
  const pathname = usePathname();
  return <div className="min-h-screen bg-[#F1F3F6] text-gray-800 font-sans">
    <header className="sticky top-0 z-40 border-b border-gray-200 bg-white"><div className={`mx-auto flex ${compact || decision ? "max-w-6xl" : "max-w-7xl"} min-h-16 flex-wrap items-center justify-between gap-4 px-4 sm:px-6 py-3`}>
      <Link href="/"><Image src="/logo.png" alt="PartPilot" width={130} height={46} className="h-8 w-auto" /></Link>
      <nav aria-label="Menu utama" className="flex flex-wrap items-center gap-2 text-sm">{[{ href: "/", name: "Beranda" }, { href: "/technician/", name: "Teknisi" }, { href: "/manager/", name: "Meja manajer" }].map(item => <Link key={item.href} href={item.href} aria-current={(item.href === "/" ? pathname === "/" : pathname.startsWith(item.href.slice(0, -1))) ? "page" : undefined} className={`rounded-lg px-3 py-2 font-semibold transition-colors ${(item.href === "/" ? pathname === "/" : pathname.startsWith(item.href.slice(0, -1))) ? "bg-blue-50 text-[#0F274A]" : "text-gray-500 hover:bg-gray-50 hover:text-[#0F274A]"}`}>{item.name}</Link>)}
        <span aria-hidden="true" className="hidden h-9 w-9 items-center justify-center rounded-full border border-[#BAE6FD] bg-[#E0F2FE] text-[#0284C7] sm:flex"><UserRound size={19} /></span></nav>
    </div></header>
    <div className="border-b border-blue-100 bg-blue-50/70 px-5 py-2 text-center text-xs text-[#17375E]">Bukti OEM terpublikasi • Inventori dan operasi simulasi • Keputusan memerlukan persetujuan • Pembelian belum dieksekusi</div>
    <main className={`mx-auto ${compact ? "max-w-5xl" : decision ? "max-w-6xl" : "max-w-7xl"} space-y-5 px-4 sm:px-6 py-6 sm:py-8`}><div className="flex flex-wrap items-center justify-between gap-4"><div><h1 className="text-xl sm:text-2xl font-bold uppercase tracking-tight text-[#0F274A]">{title}</h1><p className="mt-0.5 text-xs sm:text-sm text-gray-500"><Link href="/" className="hover:underline">Home</Link><span className="mx-1.5 text-gray-400">&gt;</span>{title}</p></div>{titleAction || ((compact || decision) && <Link href={decision ? "/manager/" : "/"} className={accent}><ArrowLeft size={16} />Kembali</Link>)}</div>{children}</main>

  </div>;
}
