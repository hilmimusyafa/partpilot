"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus, Search } from "lucide-react";
import { api, errorMessage, label, type DemoConfig, type Orders } from "@/lib/partpilot";
import { card, DemoShell, ErrorNotice, primary, secondary } from "./demo-shell";

export default function OrderList() {
  const [config, setConfig] = useState<DemoConfig | null>(null);
  const [orders, setOrders] = useState<Orders | null>(null);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  useEffect(() => {
    let active = true; let timer: ReturnType<typeof setTimeout> | undefined;
    async function load() {
      try {
        const [c, o] = await Promise.all([api<DemoConfig>("/demo/config"), api<Orders>("/demo/orders")]);
        if (!active) return;
        setConfig(c); setOrders(o); setError(""); timer = setTimeout(load, 5000);
      } catch (e) { if (active) setError(errorMessage(e)); }
    }
    void load(); return () => { active = false; clearTimeout(timer); };
  }, [refresh]);
  const rows = orders?.items || [];
  const tabs = [
    { id: "all", name: "Semua", matches: () => true },
    { id: "processing", name: "AI memproses", matches: (order: Orders["items"][number]) => ["queued", "processing"].includes(order.state) },
    { id: "awaiting", name: "Perlu tindakan", matches: (order: Orders["items"][number]) => ["draft", "awaiting_clarification", "identified"].includes(order.state) && !order.decision },
    { id: "review", name: "Perlu pemeriksaan", matches: (order: Orders["items"][number]) => ["needs_review", "no_match", "failed", "knowledge_unavailable"].includes(order.state) },
  ];
  const filtered = rows.filter(order => tabs.find(tab => tab.id === filter)!.matches(order) && `${order.id} ${order.description} ${order.identified_item_code || ""}`.toLocaleLowerCase("id-ID").includes(query.toLocaleLowerCase("id-ID")));
  return <DemoShell title="Meja manajer" config={config}>
    <div className="flex flex-wrap items-center justify-between gap-3"><p className="text-sm text-slate-600">Riwayat diperbarui otomatis setiap 5 detik.</p><label className="relative w-full sm:w-80"><Search size={16} className="absolute left-3 top-3.5 text-gray-400" /><span className="sr-only">Cari work order</span><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Cari work order…" className="h-11 w-full rounded-xl border border-gray-300 bg-white pl-9 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-[#17375E]" /></label></div>
    <ErrorNotice message={error} />
    <div className="flex flex-wrap items-center justify-between gap-4"><div className="flex flex-wrap gap-2" aria-label="Filter status work order">{tabs.map(tab => <button key={tab.id} aria-pressed={filter === tab.id} onClick={() => setFilter(tab.id)} className={`cursor-pointer rounded-xl border border-[#0F274A] px-4 py-2 text-xs sm:text-sm font-semibold ${filter === tab.id ? "bg-[#0F274A] text-white shadow-xs" : "bg-white text-[#0F274A] hover:bg-blue-50"}`}>{tab.name} ({rows.filter(tab.matches).length})</button>)}</div><div className="flex gap-3"><button className={secondary} onClick={() => setRefresh(v => v + 1)}>Muat ulang</button><Link href="/technician/" className={primary}><Plus size={16} className="mr-2" />Buat work order</Link></div></div>
    <section className={`${card} overflow-x-auto`}>
      <h2 className="mb-4 text-lg font-bold">Daftar work order</h2>
      {!orders && !error && <p role="status">Memuat work order…</p>}
      {orders && rows.length === 0 && <div className="py-12 text-center"><h3 className="font-semibold">Demo siap dimulai</h3><p className="mt-2 text-sm text-slate-500">Belum ada work order. Mulai dari skenario bearing pada form teknisi.</p><Link href="/technician/" className={`${primary} mt-5`}>Mulai skenario bearing</Link></div>}
      {rows.length > 0 && filtered.length === 0 && <p className="py-8 text-center text-sm text-gray-500">Tidak ada WO yang sesuai pencarian atau filter.</p>}
      {filtered.length > 0 && <table className="w-full min-w-[720px] text-left text-sm"><thead className="border-b border-gray-200 bg-[#EAECEF] text-xs uppercase tracking-wider text-gray-700"><tr>{["Kebutuhan", "Gudang / jumlah", "Status", "Pilihan", "Tindakan"].map(h => <th key={h} className="px-3 py-3">{h}</th>)}</tr></thead><tbody>{filtered.map(o => <tr key={o.id} className="border-b border-slate-100 last:border-0 hover:bg-blue-50/30">
        <td className="max-w-sm px-3 py-4"><p className="font-semibold">{o.description}</p><p className="mt-1 text-xs text-slate-500">{o.id.slice(0, 8)} • {o.identified_item_code || "Identitas belum ditetapkan"}</p></td><td className="px-3 py-4">{o.warehouse_id}<br /><span className="text-slate-500">{o.quantity} buah</span></td><td className="px-3 py-4">{label(o.state)}</td><td className="px-3 py-4">{o.decision?.option_id || "Belum dipilih"}</td><td className="px-3 py-4"><Link className="font-semibold text-blue-700 hover:underline" href={o.state === "identified" ? `/manager/decision/?session=${o.id}` : `/technician/clarification/?session=${o.id}`}>{o.state === "identified" ? "Buka perbandingan" : "Buka WO"} →</Link></td>
      </tr>)}</tbody></table>}
    </section>
  </DemoShell>;
}
