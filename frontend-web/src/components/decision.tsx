"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { CheckCircle2, LoaderCircle } from "lucide-react";
import { api, dateTime, errorMessage, label, money, stockQuantity, type Comparison, type DemoConfig, type Option, type Orders, type Run, type Session, type WhatsAppConversation, type WhatsAppConversations, type WhatsAppStatus } from "@/lib/partpilot";
import { card, DemoShell, ErrorNotice, primary, secondary } from "./demo-shell";
import { WhatsAppConversationsView } from "./whatsapp-conversations";

function DecisionContent() {
  const params = useSearchParams(); const sessionId = params.get("session");
  const [config, setConfig] = useState<DemoConfig | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [selected, setSelected] = useState("");
  const [confirm, setConfirm] = useState<Option | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [whatsApp, setWhatsApp] = useState<WhatsAppStatus | null>(null);
  const [conversations, setConversations] = useState<WhatsAppConversation[]>([]);
  const liveRunId = run?.transport === "whatsapp" ? run.id : null;
  const readyForWhatsApp = whatsApp?.can_start && (whatsApp.connection === "connected" || whatsApp.connection === "open");
  const waitingForVendors = run?.transport === "whatsapp" && (run.vendors.length === 0 || run.vendors.some(vendor => ["waiting", "partial", "pending"].includes(vendor.outcome) || vendor.ineligible_reasons?.includes("negotiation_pending") || (vendor.outcome === "quoted" && vendor.counteroffers_used === 0)));
  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const [c, orders] = await Promise.all([api<DemoConfig>("/demo/config"), api<Orders>("/demo/orders")]);
        if (!active) return;
        setConfig(c);
        const found = orders.items.find(o => o.id === sessionId);
        if (!found) { if (sessionId) setError("WO tidak ditemukan. Demo mungkin sudah direset."); return; }
        setSession(found); setSelected(found.decision?.option_id || "");
        const [r, comp] = await Promise.all([found.run_id ? api<Run>(`/demo/sourcing-runs/${found.run_id}`) : Promise.resolve(null), found.comparison_id ? api<Comparison>(`/demo/comparisons/${found.comparison_id}`) : Promise.resolve(null)]);
        if (active) { setRun(r); setComparison(comp); if (r?.decision) setSelected(r.decision.option_id); }
      } catch (e) { if (active) setError(errorMessage(e)); } finally { if (active) setLoading(false); }
    }
    void load(); return () => { active = false; };
  }, [sessionId]);
  useEffect(() => {
    let active = true;
    api<WhatsAppStatus>("/whatsapp/status").then(value => { if (active) setWhatsApp(value); }).catch(() => { /* Status page provides connection errors; simulator is still available. */ });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    if (!liveRunId) return;
    const runId = liveRunId;
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try {
        const [next, chats] = await Promise.all([api<Run>(`/demo/sourcing-runs/${runId}`), api<WhatsAppConversations>("/whatsapp/conversations")]);
        if (active) { setRun(next); setConversations(chats.conversations.filter(chat => chat.run_id === runId)); }
      } catch (e) { if (active) setError(errorMessage(e)); }
      finally { if (active) timer = setTimeout(poll, 5000); }
    }
    void poll();
    return () => { active = false; clearTimeout(timer); };
  }, [liveRunId]);
  async function checkStock() {
    if (!session || busy) return;
    setBusy(true); setError("");
    try { setRun(await api<Run>("/demo/sourcing-runs", { session_id: session.id, expected_version: session.version }, `source-${session.id}-${session.version}`)); }
    catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  async function startWhatsApp() {
    if (!run || busy || !readyForWhatsApp) return;
    setBusy(true); setError("");
    try {
      const chats = await api<WhatsAppConversations>(`/whatsapp/runs/${run.id}/start`, {});
      setConversations(chats.conversations.filter(chat => chat.run_id === run.id));
      setRun(await api<Run>(`/demo/sourcing-runs/${run.id}`));
      setComparison(null);
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  async function prepare() {
    if (!session || busy) return;
    setBusy(true); setError("");
    try {
      const started = run || await api<Run>("/demo/sourcing-runs", { session_id: session.id, expected_version: session.version }, `source-${session.id}-${session.version}`);
      setRun(started);
      const ready = started.transport === "whatsapp" || started.status === "fulfilled_source" ? started : await api<Run>(`/demo/sourcing-runs/${started.id}/advance`, {}); setRun(ready);
      const result = await api<Comparison>(`/demo/sourcing-runs/${started.id}/prepare-comparison`, {}, `comparison-${ready.id}-${ready.version}`); setComparison(result);
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  async function choose() {
    if (!comparison || !confirm || busy) return;
    setBusy(true); setError("");
    try {
      const result = await api<{ option_id: string }>(`/demo/comparisons/${comparison.id}/decision`, { expected_version: comparison.version, option_id: confirm.option_id, acknowledgment: "demo_only" }, `decision-${comparison.id}-${confirm.option_id}`);
      setSelected(result.option_id); setConfirm(null);
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  return <DemoShell title="Perbandingan sumber & keputusan manajer" config={config}>
    <div><Link href="/manager/" className="text-sm font-semibold text-blue-700 hover:underline">← Kembali ke daftar WO</Link></div>
    <ErrorNotice message={error} />
    {loading && <p role="status">Memuat hasil dari server…</p>}
    {!sessionId && !loading && <section className={card}><p>Pilih work order dari daftar untuk membuka perbandingan.</p><Link href="/manager/" className={`${primary} mt-4`}>Pilih work order</Link></section>}
    {session && <section className={`${card} space-y-3`}><div className="flex flex-wrap justify-between gap-3"><div><p className="text-xs text-slate-500 break-all">WO {session.id}</p><h2 className="mt-2 text-xl font-bold">{session.description}</h2><p className="mt-2 text-sm text-slate-600">{session.quantity} buah • Gudang asal {session.warehouse_id}</p></div><span className="text-sm font-semibold">{label(session.state)}</span></div>
      {session.state !== "identified" ? <Link href={`/technician/clarification/?session=${session.id}`} className={primary}>Selesaikan identifikasi terlebih dahulu</Link> : !run && <div className="space-y-3"><p className="text-sm text-slate-600">Cek stok asal dan cari bearing yang sama di gudang lain. Setelah itu, pilih pencarian vendor melalui WhatsApp atau simulator.</p><button className={primary} disabled={busy || !config} onClick={checkStock}>{busy ? <><LoaderCircle size={17} className="mr-2 animate-spin" />Memeriksa stok…</> : "Cek stok & sumber gudang"}</button></div>}
      {run?.status === "fulfilled_source" && <p className="rounded-xl bg-emerald-50 p-3 text-sm">Stok gudang asal mencukupi. Vendor tidak dihubungi. Ini belum berarti mesin selesai diperbaiki.</p>}
    </section>}
    {run && !selected && <section className={`${card} space-y-4`}><h2 className="text-lg font-bold text-[#0F274A]">{run.status === "fulfilled_source" ? "Bandingkan sumber yang tersedia" : run.transport === "whatsapp" ? "Pencarian vendor melalui WhatsApp nyata" : "Pilih cara mencari penawaran vendor"}</h2>
      {run.status !== "fulfilled_source" && run.transport !== "whatsapp" && !comparison && <><p className="text-sm text-gray-600">Tindakan WhatsApp mengirim permintaan penawaran ke vendor yang dikonfigurasi. Balasan asli diperlukan untuk melengkapi harga, stok, ongkir, pajak, dan estimasi tiba.</p><div className="flex flex-wrap gap-3"><button className={primary} disabled={busy || !config || !readyForWhatsApp} onClick={startWhatsApp}>{busy ? "Memproses…" : "Hubungi vendor via WhatsApp"}</button><Link href="/whatsapp/" className={secondary}>Koneksi & QR WhatsApp</Link></div>{!readyForWhatsApp && <p className="text-sm text-amber-800">{whatsApp?.blocked_reason || "Buka halaman WhatsApp untuk memeriksa kesiapan koneksi dan vendor."}</p>}<div className="border-t border-gray-100 pt-4"><p className="mb-3 text-xs text-gray-500">Simulator opsional memakai jawaban sintetis dan tidak mengirim pesan WhatsApp.</p><button className={secondary} disabled={busy} onClick={prepare}>Jalankan simulator & bandingkan</button></div></>}
      {(run.transport === "whatsapp" || run.status === "fulfilled_source") && <><p className="text-sm text-gray-600">{run.transport === "whatsapp" ? "Status dan balasan diperbarui otomatis. Vendor yang belum menjawab tetap menunggu; stok dan harganya belum diketahui. Anda bisa membandingkan data yang tersedia. Penawaran belum lengkap atau masih dinegosiasikan tidak dapat dipilih." : "Stok gudang asal memenuhi kebutuhan. Siapkan perbandingan tanpa menghubungi vendor."}</p><button className={primary} disabled={busy || !config} onClick={prepare}>{busy ? "Menyiapkan…" : waitingForVendors ? "Bandingkan data yang tersedia" : comparison ? "Perbarui perbandingan" : "Siapkan perbandingan"}</button></>}
      {comparison && run.transport !== "whatsapp" && run.status !== "fulfilled_source" && <p className="text-sm text-gray-600">Perbandingan ini menggunakan penawaran simulator. Gunakan WO baru untuk mencoba vendor WhatsApp nyata.</p>}
    </section>}
    {run && <section className={`${card} space-y-4`}><div><h2 className="text-lg font-bold">Pencarian stok kanonik</h2><p className="mt-1 text-sm text-slate-600">Identitas: {run.identity.brand} {run.identity.base}{run.identity.suffix}. Perbedaan kode gudang dipetakan melalui aturan penamaan.</p></div><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{[run.availability.origin, ...run.availability.alternatives].map(scope => <div key={scope.warehouse_id} className="rounded-xl border border-slate-200 p-4"><h3 className="font-semibold">{scope.warehouse_id}</h3><p className="mt-2 text-xs text-slate-500 break-all">{scope.item_code || "Kode belum ditemukan"}</p><p className="mt-2 text-xs text-slate-600">{scope.evidence?.[0]?.item_name}</p><p className="mt-3 text-lg font-bold">{stockQuantity(scope.available_qty)} <span className="text-xs font-normal">buah tersedia</span></p><p className="mt-1 text-xs text-slate-500">Fisik {stockQuantity(scope.actual_qty)} • Direservasi {stockQuantity(scope.reserved_qty)}</p><p className="mt-2 text-xs">{label(scope.status)}</p></div>)}</div>{!run.availability.complete && <p className="text-sm text-amber-800">Cakupan gudang belum lengkap. Aturan yang belum tersedia bukan bukti stok kosong.</p>}</section>}
    {run && run.vendors.length > 0 && <section className={`${card} overflow-x-auto`}><h2 className="text-lg font-bold">{run.transport === "whatsapp" ? "Penawaran WhatsApp nyata" : "Penawaran simulator"}</h2><p className="mb-4 mt-1 text-sm text-slate-600">{run.transport === "whatsapp" ? "Hanya penawaran dari balasan vendor yang ditampilkan. Maksimal satu counteroffer per vendor." : "Data sintetis, maksimal satu counteroffer per vendor. Tidak ada pesan WhatsApp nyata."}</p><table className="w-full min-w-[850px] text-left text-sm"><thead className="border-b border-gray-200 bg-[#EAECEF] text-xs uppercase text-gray-700"><tr>{["Vendor", "Hasil", "Stok", "Harga awal / buah", "Harga akhir / buah", "Counteroffer"].map(h => <th key={h} className="px-3 py-3">{h}</th>)}</tr></thead><tbody>{run.vendors.map(v => <tr key={v.vendor_id} className="border-b border-slate-100"><td className="px-3 py-4 font-semibold">{v.vendor_id}</td><td className="px-3 py-4">{run.transport === "whatsapp" && v.outcome === "pending" ? "Menunggu penawaran lengkap" : label(v.outcome)}</td><td className="px-3 py-4">{stockQuantity(v.quote?.qty_available)}</td><td className="px-3 py-4">{money(v.initial_quote?.unit_price)}</td><td className="px-3 py-4">{money(v.quote?.unit_price)}</td><td className="px-3 py-4">{v.counteroffers_used} / 1</td></tr>)}</tbody></table></section>}
    {run?.transport === "whatsapp" && <section className={`${card} space-y-4`}><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-bold">Percakapan vendor</h2><Link href="/whatsapp/" className="text-sm font-semibold text-[#17375E] hover:underline">Buka WhatsApp →</Link></div>{conversations.length ? <WhatsAppConversationsView conversations={conversations} recipients={whatsApp?.recipients} /> : <p className="text-sm text-gray-500">Memuat percakapan untuk pencarian ini…</p>}</section>}
    {comparison && <>
      <section className={`${card} space-y-4`}><h2 className="text-lg font-bold">Biaya total sampai produksi pulih</h2><p className="text-sm text-slate-600">Barang / pengisian ulang + ongkir + pajak + biaya pemulihan tambahan + kontribusi produksi yang hilang. Angka untuk demo; harga pasar dan waktu aktual perlu diverifikasi.</p>{typeof config?.assumptions.summary === "string" && <p className="rounded-xl bg-blue-50 p-4 text-sm">{config.assumptions.summary}</p>}
        {selected && <p role="status" className="flex items-center gap-2 rounded-xl bg-emerald-50 p-4 font-semibold"><CheckCircle2 size={20} />Pilihan tercatat: {selected}. Tidak ada pembelian atau mutasi stok yang dieksekusi.</p>}
        {comparison.eligible_complete_options.length === 0 && <p className="rounded-xl bg-amber-50 p-4 text-sm">Belum ada opsi yang memenuhi kebutuhan dan memiliki data biaya lengkap. Manajer belum bisa memilih.</p>}
        <div className="grid gap-4 lg:grid-cols-2">{comparison.eligible_complete_options.map((option, index) => <article key={option.option_id} className={`rounded-2xl border p-5 ${selected === option.option_id ? "border-emerald-400 bg-emerald-50" : "border-slate-200"}`}>
          <div className="flex items-center justify-between gap-2"><h3 className="font-bold">{option.source_id}</h3><span className="rounded-full bg-slate-100 px-3 py-1 text-xs">{index === 0 ? "Total terendah di opsi lengkap" : option.source_kind === "warehouse" ? "Sumber gudang" : run?.transport === "whatsapp" ? "Vendor WhatsApp" : "Vendor simulator"}</span></div>
          <p className="mt-1 text-xs text-slate-500">{option.item_code || "Barang identik sesuai permintaan"}</p>
          <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm"><dt>Harga per buah</dt><dd className="text-right">{money(option.quote?.unit_price)}</dd><dt>Ongkir</dt><dd className="text-right">{money(option.quote?.shipping_amount)}</dd><dt>Pajak penawaran</dt><dd className="text-right">{money(option.quote?.tax_amount)}</dd><dt>Barang + ongkir + pajak</dt><dd className="text-right">{money(option.economics?.sourcing_total)}</dd><dt>Kontribusi yang hilang</dt><dd className="text-right">{money(option.economics?.unrecoverable_lost_contribution)}</dd><dt>Pemulihan tambahan</dt><dd className="text-right">{money(option.economics?.incremental_disruption_total)}</dd><dt className="border-t border-slate-200 pt-3 font-bold">Total relevan</dt><dd className="border-t border-slate-200 pt-3 text-right text-lg font-bold">{money(option.economics?.future_relevant_option_total)}</dd></dl>
          <p className="mt-4 text-xs text-slate-500">Estimasi tiba: {dateTime(option.quote?.delivered_eta)}<br />Pulih setelah pemasangan & restart: {dateTime(option.assumptions?.schedule?.stages?.find(s => s.kind === "restart")?.end)}<br />Berlaku sampai: {dateTime(option.valid_until)}</p>
          <button className={`${primary} mt-4 w-full`} disabled={busy || !!selected || !comparison.unexpired_option_ids.includes(option.option_id)} onClick={() => setConfirm(option)}>{selected === option.option_id ? "Sudah dipilih" : !comparison.unexpired_option_ids.includes(option.option_id) ? "Penawaran kedaluwarsa" : "Pilih sumber ini"}</button>
        </article>)}</div>
      </section>
      {comparison.unrankable_options.length > 0 && <section className={`${card} space-y-3`}><h2 className="font-bold">Opsi yang belum bisa dipilih</h2><ul className="space-y-2 text-sm">{comparison.unrankable_options.map(o => <li key={o.option_id} className="rounded-xl bg-slate-50 p-3"><strong>{o.source_id}</strong> — {(o.reasons || []).map(label).join("; ")}</li>)}</ul></section>}
    </>}
    {confirm && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-5"><section role="dialog" aria-modal="true" aria-labelledby="decision-heading" className={`${card} max-w-lg space-y-4`}><h2 id="decision-heading" className="text-xl font-bold">Pilih {confirm.source_id}?</h2><p className="text-sm">Pilihan ini dicatat sebagai keputusan demo untuk seluruh {session?.quantity} buah. Sistem akan memeriksa kembali stok atau validitas penawaran. Tidak ada PO atau mutasi nyata.</p><ErrorNotice message={error} /><div className="flex justify-end gap-3"><button className={secondary} disabled={busy} onClick={() => setConfirm(null)}>Batal</button><button className={primary} disabled={busy} onClick={choose}>{busy ? "Menyimpan…" : "Konfirmasi pilihan demo"}</button></div></section></div>}
  </DemoShell>;
}
export default function Decision() { return <Suspense fallback={<p className="p-8">Memuat perbandingan…</p>}><DecisionContent /></Suspense>; }
