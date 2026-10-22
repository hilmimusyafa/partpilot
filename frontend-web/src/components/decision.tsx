"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { CheckCircle2, LoaderCircle } from "lucide-react";
import { api, errorMessage, label, money, stockQuantity, type Comparison, type DemoConfig, type Option, type Orders, type PurchaseOrder, type PurchaseOrderResult, type Run, type Session, type WhatsAppConversation, type WhatsAppConversations, type WhatsAppStatus } from "@/lib/partpilot";
import { card, DemoShell, ErrorNotice, primary, secondary } from "./demo-shell";
import { PurchaseOrderCard, SourceComparison, SourceRecommendation } from "./source-comparison";
import { WhatsAppConversationsView } from "./whatsapp-conversations";

function negotiationStatus(run: Run, vendor: Run["vendors"][number]): string {
  const availableQuantity = vendor.quote?.qty_available;
  if (["insufficient_stock", "no_stock"].includes(vendor.outcome)
    || vendor.ineligible_reasons?.includes("insufficient_stock")
    || (availableQuantity != null && Number(availableQuantity) < Number(run.quantity))) return "Stok tidak mencukupi — tidak ditawar";
  if (vendor.outcome === "no_response") return "Menunggu balasan vendor — belum ditawar";
  if (vendor.ineligible_reasons?.includes("negotiation_pending")) return "Menunggu jawaban negosiasi";
  const plan = run.negotiation?.vendors.find(item => item.vendor_id === vendor.vendor_id);
  if (plan?.status === "skipped") return "Dilewati — " + (plan.reason ? label(plan.reason) : "target tidak lebih baik");
  if (["revised_quote", "negotiation_refused"].includes(vendor.outcome)) return "Selesai — harga akhir siap";
  if (vendor.eligible) return "Siap dibandingkan";
  if (plan?.status === "planned") return "Target negosiasi tersedia";
  return "Menunggu penawaran lengkap";
}

function DecisionContent() {
  const params = useSearchParams(); const sessionId = params.get("session");
  const [config, setConfig] = useState<DemoConfig | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [selected, setSelected] = useState("");
  const [confirm, setConfirm] = useState<Option | null>(null);
  const [purchaseOrder, setPurchaseOrder] = useState<PurchaseOrder | null>(null);
  const [poError, setPoError] = useState("");
  const [poBusy, setPoBusy] = useState(false);
  const [warehouseConfirmation, setWarehouseConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [whatsApp, setWhatsApp] = useState<WhatsAppStatus | null>(null);
  const [conversations, setConversations] = useState<WhatsAppConversation[]>([]);
  const liveRunId = run?.transport === "whatsapp" ? run.id : null;
  const readyForWhatsApp = whatsApp?.can_start && (whatsApp.connection === "connected" || whatsApp.connection === "open");
  const waitingForVendors = run?.transport === "whatsapp" && (run.vendors.length === 0 || run.vendors.some(vendor => ["waiting", "partial", "pending"].includes(vendor.outcome) || vendor.ineligible_reasons?.includes("negotiation_pending")));
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
  async function loadPurchaseOrder(runId: string) {
    setPoBusy(true); setPoError("");
    try { const result = await api<PurchaseOrderResult>(`/demo/sourcing-runs/${runId}/purchase-order`); setPurchaseOrder(result.purchase_order); }
    catch (e) { setPoError(errorMessage(e)); } finally { setPoBusy(false); }
  }
  const selectedOption = comparison?.eligible_complete_options.find(option => option.option_id === selected);
  const selectedVendor = selectedOption?.source_kind === "vendor";
  const selectedRunId = selectedVendor ? run?.id : undefined;
  useEffect(() => {
    if (!selectedRunId) return;
    let active = true;
    api<PurchaseOrderResult>(`/demo/sourcing-runs/${selectedRunId}/purchase-order`).then(result => { if (active) { setPurchaseOrder(result.purchase_order); setPoError(""); } }).catch(e => { if (active) setPoError(errorMessage(e)); });
    return () => { active = false; };
  }, [selectedRunId]);
  async function choose() {
    if (!comparison || !confirm || busy) return;
    setBusy(true); setError("");
    try {
      const result = await api<{ option_id: string }>(`/demo/comparisons/${comparison.id}/decision`, { expected_version: comparison.version, option_id: confirm.option_id, acknowledgment: "demo_only" }, `decision-${comparison.id}-${confirm.option_id}`);
      setSelected(result.option_id);
      if (confirm.source_kind === "warehouse") setWarehouseConfirmation(confirm.source_id);
      setConfirm(null);
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  return <DemoShell title="Meja keputusan" config={config} decision>
    <ErrorNotice message={error} />
    {loading && <p role="status">Memuat hasil dari server…</p>}
    {comparison && <SourceRecommendation comparison={comparison} selected={selected} busy={busy} onChoose={setConfirm} />}
    {selectedVendor && <PurchaseOrderCard purchaseOrder={purchaseOrder} error={poError} busy={poBusy} onRetry={() => { if (run) void loadPurchaseOrder(run.id); }} />}
    {!sessionId && !loading && <section className={card}><p>Pilih work order dari daftar untuk membuka perbandingan.</p><Link href="/manager/" className={`${primary} mt-4`}>Pilih work order</Link></section>}
    {session && <section className={`${card} space-y-3`}><div className="flex flex-wrap justify-between gap-3"><div><p className="text-xs text-slate-500 break-all">WO {session.id}</p><h2 className="mt-2 text-xl font-bold">{session.description}</h2><p className="mt-2 text-sm text-slate-600">{session.quantity} buah • Gudang asal {session.warehouse_id}</p></div><span className="text-sm font-semibold">{label(session.state)}</span></div>
      {session.state !== "identified" ? <Link href={`/technician/clarification/?session=${session.id}`} className={primary}>Selesaikan identifikasi terlebih dahulu</Link> : !run && <div className="space-y-3"><p className="text-sm text-slate-600">Cek stok asal dan cari bearing yang sama di gudang lain. Setelah itu, pilih pencarian vendor melalui WhatsApp atau simulator.</p><button className={primary} disabled={busy || !config} onClick={checkStock}>{busy ? <><LoaderCircle size={17} className="mr-2 animate-spin" />Memeriksa stok…</> : "Cek stok & sumber gudang"}</button></div>}
      {run?.status === "fulfilled_source" && <p className="rounded-xl bg-emerald-50 p-3 text-sm">Stok gudang asal mencukupi. Vendor tidak dihubungi. Ini belum berarti mesin selesai diperbaiki.</p>}
    </section>}
    {run && !selected && (!comparison || run.transport === "whatsapp") && <section className={`${card} space-y-4`}><h2 className="text-lg font-bold text-[#0F274A]">{run.status === "fulfilled_source" ? "Bandingkan sumber yang tersedia" : run.transport === "whatsapp" ? "Pencarian vendor melalui WhatsApp nyata" : "Pilih cara mencari penawaran vendor"}</h2>
      {run.status !== "fulfilled_source" && run.transport !== "whatsapp" && !comparison && <><p className="text-sm text-gray-600">Tindakan WhatsApp mengirim permintaan penawaran ke vendor yang dikonfigurasi. Balasan asli diperlukan untuk melengkapi harga, stok, ongkir, pajak, dan estimasi tiba.</p><div className="flex flex-wrap gap-3"><button className={primary} disabled={busy || !config || !readyForWhatsApp} onClick={startWhatsApp}>{busy ? "Memproses…" : "Hubungi vendor via WhatsApp"}</button><Link href="/whatsapp/" className={secondary}>Koneksi & QR WhatsApp</Link></div>{!readyForWhatsApp && <p className="text-sm text-amber-800">{whatsApp?.blocked_reason || "Buka halaman WhatsApp untuk memeriksa kesiapan koneksi dan vendor."}</p>}<div className="border-t border-gray-100 pt-4"><p className="mb-3 text-xs text-gray-500">Simulator opsional memakai jawaban sintetis dan tidak mengirim pesan WhatsApp.</p><button className={secondary} disabled={busy} onClick={prepare}>Jalankan simulator & bandingkan</button></div></>}
      {(run.transport === "whatsapp" || run.status === "fulfilled_source") && <><p className="text-sm text-gray-600">{run.transport === "whatsapp" ? "Status dan balasan diperbarui otomatis. Vendor yang belum menjawab tetap menunggu; stok dan harganya belum diketahui. Anda bisa membandingkan data yang tersedia. Penawaran belum lengkap atau masih dinegosiasikan tidak dapat dipilih." : "Stok gudang asal memenuhi kebutuhan. Siapkan perbandingan tanpa menghubungi vendor."}</p><button className={primary} disabled={busy || !config} onClick={prepare}>{busy ? "Menyiapkan…" : waitingForVendors ? "Bandingkan data yang tersedia" : comparison ? "Perbarui perbandingan" : "Siapkan perbandingan"}</button></>}
      {comparison && run.transport !== "whatsapp" && run.status !== "fulfilled_source" && <p className="text-sm text-gray-600">Perbandingan ini menggunakan penawaran simulator. Gunakan WO baru untuk mencoba vendor WhatsApp nyata.</p>}
    </section>}
    {comparison && <SourceComparison comparison={comparison} selected={selected} busy={busy} onChoose={setConfirm} />}
    {run && <section className={`${card} space-y-4`}><div><h2 className="text-lg font-bold">Pencarian stok kanonik</h2><p className="mt-1 text-sm text-slate-600">Identitas: {run.identity.brand} {run.identity.base}{run.identity.suffix}. Perbedaan kode gudang dipetakan melalui aturan penamaan.</p></div><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{[run.availability.origin, ...run.availability.alternatives].map(scope => <div key={scope.warehouse_id} className="rounded-xl border border-slate-200 p-4"><h3 className="font-semibold">{scope.warehouse_id}</h3><p className="mt-2 text-xs text-slate-500 break-all">{scope.item_code || "Kode belum ditemukan"}</p><p className="mt-2 text-xs text-slate-600">{scope.evidence?.[0]?.item_name}</p><p className="mt-3 text-lg font-bold">{stockQuantity(scope.available_qty)} <span className="text-xs font-normal">buah tersedia</span></p><p className="mt-1 text-xs text-slate-500">Fisik {stockQuantity(scope.actual_qty)} • Direservasi {stockQuantity(scope.reserved_qty)}</p><p className="mt-2 text-xs">{label(scope.status)}</p></div>)}</div>{!run.availability.complete && <p className="text-sm text-amber-800">Cakupan gudang belum lengkap. Aturan yang belum tersedia bukan bukti stok kosong.</p>}</section>}
    {run && run.vendors.length > 0 && <section className={`${card} overflow-x-auto`}><h2 className="text-lg font-bold">{run.transport === "whatsapp" ? "Penawaran WhatsApp nyata" : "Penawaran simulator"}</h2><p className="mb-4 mt-1 text-sm text-slate-600">{run.transport === "whatsapp" ? "Hanya penawaran dari balasan vendor yang ditampilkan. Maksimal satu penawaran harga per vendor." : "Data sintetis, maksimal satu penawaran harga per vendor. Tidak ada pesan WhatsApp nyata."}</p>{run.negotiation && <p className="mb-4 rounded-xl bg-[#F8E8B6]/60 p-3 text-sm text-[#0F274A]">Negosiasi putaran {run.negotiation.round}: total acuan {money(run.negotiation.best_total)} → target total {money(run.negotiation.target_total)} (10% lebih rendah). Target harga per buah memperhitungkan biaya selain barang dari masing-masing vendor.</p>}<table className="w-full min-w-[850px] text-left text-sm"><thead className="border-b border-gray-200 bg-[#EAECEF] text-xs uppercase text-gray-700"><tr>{["Vendor", "Hasil", "Stok", "Harga awal / buah", "Harga akhir / buah", "Negosiasi", "Tawaran harga"].map(h => <th key={h} className="px-3 py-3">{h}</th>)}</tr></thead><tbody>{run.vendors.map(v => <tr key={v.vendor_id} className="border-b border-slate-100"><td className="px-3 py-4 font-semibold">{v.vendor_id}</td><td className="px-3 py-4">{run.transport === "whatsapp" && v.outcome === "pending" ? "Menunggu penawaran lengkap" : label(v.outcome)}</td><td className="px-3 py-4">{stockQuantity(v.quote?.qty_available)}</td><td className="px-3 py-4">{money(v.initial_quote?.unit_price)}</td><td className="px-3 py-4">{money(v.quote?.unit_price)}</td><td className="px-3 py-4"><p>{negotiationStatus(run, v)}</p>{run.negotiation?.vendors.find(plan => plan.vendor_id === v.vendor_id)?.target_unit_price && <p className="mt-1 text-xs text-gray-500">Target {money(run.negotiation.vendors.find(plan => plan.vendor_id === v.vendor_id)?.target_unit_price)} / buah</p>}</td><td className="px-3 py-4">{v.counteroffers_used} / 1</td></tr>)}</tbody></table></section>}
    {run?.transport === "whatsapp" && <section className={`${card} space-y-4`}><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-bold">Percakapan vendor</h2><Link href="/whatsapp/" className="text-sm font-semibold text-[#17375E] hover:underline">Buka WhatsApp →</Link></div>{conversations.length ? <WhatsAppConversationsView conversations={conversations} recipients={whatsApp?.recipients} /> : <p className="text-sm text-gray-500">Memuat percakapan untuk pencarian ini…</p>}</section>}
    {confirm && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-5"><section role="dialog" aria-modal="true" aria-labelledby="decision-heading" className="w-full max-w-md space-y-4 rounded-3xl border border-gray-100 bg-white p-6 shadow-2xl sm:p-8"><h2 id="decision-heading" className="text-xl font-bold text-[#0F274A]">{confirm.source_kind === "vendor" ? "Setujui Purchase Order demo?" : "Pilih sumber gudang?"}</h2><p className="text-sm">Pilih {confirm.source_id} untuk seluruh {session?.quantity} buah. Sistem akan memeriksa kembali stok atau validitas penawaran.</p><p className="text-sm text-gray-600">{confirm.source_kind === "vendor" ? "Persetujuan ini membuat PO demo PT PartPilot dari harga dan jumlah yang disetujui. Dokumen tidak dikirim otomatis melalui email atau WhatsApp." : "Pilihan gudang hanya dicatat sebagai keputusan demo. Stok tidak dipindahkan dan PO tidak dibuat."}</p><ErrorNotice message={error} /><div className="flex justify-end gap-3"><button className={secondary} disabled={busy} onClick={() => setConfirm(null)}>Batal</button><button className={primary} disabled={busy} onClick={choose}>{busy ? "Menyimpan…" : confirm.source_kind === "vendor" ? "Konfirmasi PO demo" : "Konfirmasi pilihan gudang"}</button></div></section></div>}
    {warehouseConfirmation && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-5"><section role="dialog" aria-modal="true" aria-labelledby="warehouse-confirmation" className="w-full max-w-md space-y-4 rounded-3xl border border-gray-100 bg-white p-6 text-center shadow-2xl sm:p-8"><CheckCircle2 className="mx-auto h-12 w-12 rounded-2xl bg-emerald-100 p-3 text-emerald-700" /><h2 id="warehouse-confirmation" className="text-xl font-bold text-[#0F274A]">Pilihan gudang tercatat</h2><p className="text-sm">{warehouseConfirmation} dipilih untuk {session?.quantity} buah. Keputusan ini tidak memindahkan stok dan tidak membuat PO.</p><button autoFocus className={primary} onClick={() => setWarehouseConfirmation("")}>Selesai</button></section></div>}
  </DemoShell>;
}
export default function Decision() { return <Suspense fallback={<p className="p-8">Memuat perbandingan…</p>}><DecisionContent /></Suspense>; }
