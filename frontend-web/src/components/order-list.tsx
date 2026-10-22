"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, errorMessage, label, type DemoConfig, type Orders } from "@/lib/partpilot";
import { card, DemoShell, ErrorNotice, primary, secondary } from "./demo-shell";

export default function OrderList() {
  const [config, setConfig] = useState<DemoConfig | null>(null);
  const [orders, setOrders] = useState<Orders | null>(null);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
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
  return <DemoShell title="Meja manajer" config={config}>
    <div className="flex flex-wrap items-center justify-between gap-3"><p className="text-sm text-slate-600">Riwayat tersimpan di server dan diperbarui otomatis setiap 5 detik.</p><div className="flex gap-3"><button className={secondary} onClick={() => setRefresh(v => v + 1)}>Muat ulang</button><Link href="/technician/" className={primary}>Buat work order</Link></div></div>
    <ErrorNotice message={error} />
    <div className="grid gap-4 sm:grid-cols-3">{[
      ["Work order aktif", rows.length], ["Menunggu klarifikasi", rows.filter(o => o.state === "awaiting_clarification").length], ["Pilihan manajer tercatat", rows.filter(o => o.decision).length],
    ].map(([name, value]) => <div key={name} className={card}><p className="text-sm text-slate-500">{name}</p><p className="mt-2 text-3xl font-bold">{value}</p></div>)}</div>
    <section className={`${card} overflow-x-auto`}>
      <h2 className="mb-4 text-lg font-bold">Daftar work order</h2>
      {!orders && !error && <p role="status">Memuat work order…</p>}
      {orders && rows.length === 0 && <div className="py-12 text-center"><h3 className="font-semibold">Demo siap dimulai</h3><p className="mt-2 text-sm text-slate-500">Belum ada work order. Mulai dari skenario bearing pada form teknisi.</p><Link href="/technician/" className={`${primary} mt-5`}>Mulai skenario bearing</Link></div>}
      {rows.length > 0 && <table className="w-full min-w-[720px] text-left text-sm"><thead className="border-b border-slate-200 text-xs uppercase text-slate-500"><tr>{["Kebutuhan", "Gudang / jumlah", "Status", "Pilihan", "Tindakan"].map(h => <th key={h} className="px-3 py-3">{h}</th>)}</tr></thead><tbody>{rows.map(o => <tr key={o.id} className="border-b border-slate-100 last:border-0">
        <td className="max-w-sm px-3 py-4"><p className="font-semibold">{o.description}</p><p className="mt-1 text-xs text-slate-500">{o.id.slice(0, 8)} • {o.identified_item_code || "Identitas belum ditetapkan"}</p></td><td className="px-3 py-4">{o.warehouse_id}<br /><span className="text-slate-500">{o.quantity} buah</span></td><td className="px-3 py-4">{label(o.state)}</td><td className="px-3 py-4">{o.decision?.option_id || "Belum dipilih"}</td><td className="px-3 py-4"><Link className="font-semibold text-blue-700 hover:underline" href={o.state === "identified" ? `/manager/decision/?session=${o.id}` : `/technician/clarification/?session=${o.id}`}>{o.state === "identified" ? "Buka perbandingan" : "Buka WO"} →</Link></td>
      </tr>)}</tbody></table>}
    </section>
  </DemoShell>;
}
