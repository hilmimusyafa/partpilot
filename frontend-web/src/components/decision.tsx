"use client";
import { Suspense, useEffect, useEffectEvent, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { CheckCircle2, LoaderCircle } from "lucide-react";
import { api, ApiError, errorMessage, label, money, stockQuantity, sourceName, warehouseName, type Comparison, type DemoConfig, type Option, type PurchaseOrder, type PurchaseOrderResult, type Run, type Session, type WhatsAppConversation, type WhatsAppConversations, type WhatsAppStatus } from "@/lib/partpilot";
import { card, DemoShell, ErrorNotice, field, primary, secondary } from "./demo-shell";
import { PurchaseOrderCard, SourceComparison, SourceRecommendation } from "./source-comparison";
import { WarehouseStock } from "./warehouse-stock";
import { useLiveComparison } from "./use-live-comparison";
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

function DecisionContent({ sessionId }: { sessionId: string | null }) {
  const [config, setConfig] = useState<DemoConfig | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [benchmarkAck, setBenchmarkAck] = useState(false);
  const [mapping, setMapping] = useState("18000");
  const foodRun = run?.identity.unit_scope === "complete_housed_unit";
  const [selected, setSelected] = useState("");
  const [confirm, setConfirm] = useState<Option | null>(null);
  const [confirmationComparison, setConfirmationComparison] = useState<Comparison | null>(null);
  const [confirmationInvalid, setConfirmationInvalid] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [purchaseOrder, setPurchaseOrder] = useState<PurchaseOrder | null>(null);
  const [poError, setPoError] = useState("");
  const [poBusy, setPoBusy] = useState(false);
  const [warehouseConfirmation, setWarehouseConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [whatsApp, setWhatsApp] = useState<WhatsAppStatus | null>(null);
  const [automationError, setAutomationError] = useState<"stock" | "whatsapp" | null>(null);
  const stockAttempt = useRef("");
  const whatsappAttempt = useRef("");
  const [conversations, setConversations] = useState<WhatsAppConversation[]>([]);
  const live = useLiveComparison({ run, comparison, selected, confirm, busy, setRun, setComparison, setSelected, setConversations, refresh });
  const readWorkflow = useEffectEvent(() => ({ run, comparison, selected }));
  const incompleteWhatsAppStart = run?.transport === "whatsapp" && !!whatsApp?.recipients.length && whatsApp.recipients.some(recipient => !run.vendors.some(vendor => vendor.vendor_id === recipient.id));
  const waitingForVendors = run?.transport === "whatsapp" && (run.vendors.length === 0 || run.vendors.some(vendor => ["waiting", "partial", "pending"].includes(vendor.outcome) || vendor.ineligible_reasons?.includes("negotiation_pending")));
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function load() {
      let pollAgain = true;
      try {
        const [c, found] = await Promise.all([api<DemoConfig>("/demo/config"), sessionId ? api<Session>(`/demo/orders/${encodeURIComponent(sessionId)}`) : Promise.resolve(null)]);
        if (!active) return;
        setConfig(c);
        if (!found) { pollAgain = false; return; }
        setSession(previous => previous?.id === found.id && previous.version > found.version ? previous : found);
        if (found.decision) setSelected(found.decision.option_id);
        if (found.run_id && !readWorkflow().run) {
          const [r, comp] = await Promise.all([api<Run>(`/demo/sourcing-runs/${found.run_id}`), found.comparison_id ? api<Comparison>(`/demo/comparisons/${found.comparison_id}`) : Promise.resolve(null)]);
          if (active && !readWorkflow().run) { setRun(r); setComparison(comp); if (r.decision) setSelected(r.decision.option_id); }
        }
        pollAgain = found.state !== "identified" || !found.run_id;
        setError("");
      } catch (failure) { if (active) { setError(errorMessage(failure)); if (failure instanceof ApiError && failure.status === 404) pollAgain = false; } }
      finally { if (active) { setLoading(false); if (pollAgain) timer = setTimeout(load, 5000); } }
    }
    void load(); return () => { active = false; clearTimeout(timer); };
  }, [sessionId]);
  useEffect(() => {
    let active = true;
    api<WhatsAppStatus>("/whatsapp/status").then(value => { if (active) setWhatsApp(value); }).catch(() => { if (active) setWhatsApp({ connection: "unknown", can_start: false, enabled: false, qr_data_url: null, recipients: [], blocked_reason: "Status koneksi WhatsApp belum dapat dimuat." }); });
    return () => { active = false; };
  }, []);
  async function checkStock() {
    if (!session || busy || run || session.state !== "identified") return;
    stockAttempt.current = `${session.id}-${session.version}`;
    setBusy(true); setError(""); setAutomationError(null);
    try { setRun(await api<Run>("/demo/sourcing-runs", { session_id: session.id, expected_version: session.version }, `source-${session.id}-${session.version}`)); }
    catch (e) { setError(errorMessage(e)); setAutomationError("stock"); } finally { setBusy(false); }
  }
  async function startWhatsApp(refreshStatus = false) {
    if (!run || busy || selected || run.status === "fulfilled_source") return;
    whatsappAttempt.current = run.id;
    setBusy(true); setError(""); setAutomationError(null);
    try {
      const status = refreshStatus ? await api<WhatsAppStatus>("/whatsapp/status") : whatsApp;
      if (status) setWhatsApp(status);
      if (!status?.can_start || status.connection !== "connected") throw new Error(status?.blocked_reason || "WhatsApp belum terhubung. Minta pengelola demo memeriksa koneksi, lalu coba lagi.");
      const chats = await api<WhatsAppConversations>(`/whatsapp/runs/${run.id}/start`, {});
      setConversations(chats.conversations.filter(chat => chat.run_id === run.id));
      setRun(await api<Run>(`/demo/sourcing-runs/${run.id}`));
      setComparison(null);
    } catch (e) { setError(errorMessage(e)); setAutomationError("whatsapp"); }
    finally { setBusy(false); }
  }
  const automate = useEffectEvent(() => {
    if (loading || !config || !session || selected || busy) return;
    if (session.state === "identified" && !run && stockAttempt.current !== `${session.id}-${session.version}`) { void checkStock(); return; }
    // Never turn a historical simulator result or an existing WA conversation into a new RFQ.
  });
  useEffect(() => { automate(); }, [loading, config, session, run, selected, busy, comparison, whatsApp]);
  async function prepare() {
    if (!session || busy || live.refreshing) return;
    setBusy(true); setError("");
    try {
      const started = run || await api<Run>("/demo/sourcing-runs", { session_id: session.id, expected_version: session.version }, `source-${session.id}-${session.version}`);
      setRun(started);
      const key = `manual-comparison-${started.id}-${crypto.randomUUID()}`;
      if (started.identity.unit_scope === "complete_housed_unit" && !benchmarkAck) throw new Error("Konfirmasikan penggunaan benchmark dan pemetaan simulasi terlebih dahulu.");
      const result = started.identity.unit_scope === "complete_housed_unit"
        ? await api<Comparison>(`/food-demo/sourcing-runs/${started.id}/comparison`, {external_applicability_acknowledged:true, idr_per_published_currency_unit:mapping, conversion_assumption_acknowledged:true}, key)
        : await api<Comparison>(`/demo/sourcing-runs/${started.id}/prepare-comparison`, {}, key);
      setComparison(result);
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  async function loadPurchaseOrder(runId: string) {
    setPoBusy(true); setPoError("");
    try { const result = await api<PurchaseOrderResult>(`/demo/sourcing-runs/${runId}/purchase-order`); setPurchaseOrder(result.purchase_order); }
    catch (e) { setPoError(errorMessage(e)); } finally { setPoBusy(false); }
  }
  const selectedOption = comparison?.eligible_complete_options.find(option => option.option_id === selected);
  const selectedVendor = selectedOption?.source_kind === "vendor" || selected.startsWith("vendor:");
  const selectedRunId = selectedVendor ? run?.id : undefined;
  useEffect(() => {
    if (!selectedRunId) return;
    let active = true;
    api<PurchaseOrderResult>(`/demo/sourcing-runs/${selectedRunId}/purchase-order`).then(result => { if (active) { setPurchaseOrder(result.purchase_order); setPoError(""); } }).catch(e => { if (active) setPoError(errorMessage(e)); });
    return () => { active = false; };
  }, [selectedRunId]);
  const comparisonStale = !!(run && comparison && comparison.source_run_version !== run.version && !selected);
  const confirmationStale = confirmationInvalid || !!selected || !!(run && confirmationComparison && confirmationComparison.source_run_version !== run.version);
  function openConfirmation(option: Option) {
    if (!comparison || busy || live.refreshing || comparisonStale || selected) return;
    setConfirmationComparison(comparison); setConfirmationInvalid(false); setError(""); setConfirm(option);
  }
  function closeConfirmation() { setConfirm(null); setConfirmationComparison(null); setConfirmationInvalid(false); setError(""); setRefresh(value => value + 1); }
  async function choose() {
    if (!confirmationComparison || !confirm || !run || busy || confirmationStale) return;
    setBusy(true); setError("");
    try {
      const latest = await api<Run>(`/demo/sourcing-runs/${run.id}`);
      setRun(previous => previous?.id === latest.id && previous.version > latest.version ? previous : latest);
      if (latest.decision) { setSelected(latest.decision.option_id); setConfirmationInvalid(true); setError("Keputusan untuk WO ini sudah dicatat dari sesi lain."); return; }
      if (latest.version !== confirmationComparison.source_run_version) { setConfirmationInvalid(true); setError("Penawaran berubah. Tutup konfirmasi dan tinjau perbandingan terbaru sebelum memilih lagi."); return; }
      const result = await api<{ option_id: string }>(`/demo/comparisons/${confirmationComparison.id}/decision`, { expected_version: confirmationComparison.version, option_id: confirm.option_id, acknowledgment: "demo_only" }, `decision-${confirmationComparison.id}-${confirm.option_id}`);
      setSelected(result.option_id);
      if (confirm.source_kind === "warehouse") setWarehouseConfirmation(sourceName(confirm, config));
      setConfirm(null); setConfirmationComparison(null);
    } catch (failure) { setError(errorMessage(failure)); if (failure instanceof ApiError && [409, 422].includes(failure.status)) setConfirmationInvalid(true); }
    finally { setBusy(false); }
  }
  return <DemoShell title="Meja keputusan" config={config} decision>
    <ErrorNotice message={error} />
    <ErrorNotice message={live.error} />
    {run?.transport === "whatsapp" && !selected && <p role="status" className="text-sm text-[#17375E]">{confirm && comparisonStale ? "Ada penawaran baru. Konfirmasi yang sedang dibuka tetap menampilkan pilihan sebelumnya; tutup untuk meninjau pembaruan." : foodRun ? "Balasan diperbarui setiap 5 detik. Klik perbarui perbandingan setelah penawaran berubah." : live.refreshing || comparisonStale ? "Memperbarui perbandingan dari penawaran terbaru…" : "Penawaran dan peringkat diperbarui otomatis setiap 5 detik."}</p>}
    {loading && <p role="status">Memuat hasil dari server…</p>}
    {comparison && <SourceRecommendation comparison={comparison} config={config} selected={selected} busy={busy || live.refreshing || comparisonStale} onChoose={openConfirmation} />}
    {selectedVendor && <PurchaseOrderCard purchaseOrder={purchaseOrder} error={poError} busy={poBusy} onRetry={() => { if (run) void loadPurchaseOrder(run.id); }} />}
    {!sessionId && !loading && <section className={card}><p>Pilih work order dari daftar untuk membuka perbandingan.</p><Link href="/manager/" className={`${primary} mt-4`}>Pilih work order</Link></section>}
    {session && <section className={`${card} space-y-3`}><div className="flex flex-wrap justify-between gap-3"><div><p className="text-xs text-slate-500 break-all">WO {session.id}</p><h2 className="mt-2 text-xl font-bold">{session.description}</h2><p className="mt-2 text-sm text-slate-600">{session.quantity} buah • Gudang asal {warehouseName(session.warehouse_id, config)}</p></div><span className="text-sm font-semibold">{label(session.state)}</span></div>
      {session.state !== "identified" ? <Link href={`/technician/clarification/?session=${session.id}`} className={primary}>Selesaikan identifikasi terlebih dahulu</Link> : !run && <div className="space-y-3"><p className="text-sm text-slate-600">Sistem memeriksa stok gudang asal dan gudang lain. Jika stok asal kurang, gunakan tombol pengujian untuk mengirim penawaran WhatsApp.</p>{automationError === "stock" ? <button className={primary} disabled={busy} onClick={() => void checkStock()}>Coba cek stok lagi</button> : <p role="status" className="flex items-center gap-2"><LoaderCircle size={17} className="animate-spin" />Memeriksa stok…</p>}</div>}
      {run?.status === "fulfilled_source" && <p className="rounded-xl bg-emerald-50 p-3 text-sm">Stok gudang asal mencukupi. Vendor tidak dihubungi. Ini belum berarti mesin selesai diperbaiki.</p>}
    </section>}
    {run && !selected && (!comparison || run.transport === "whatsapp") && <section className={`${card} space-y-4`}><h2 className="text-lg font-bold text-[#0F274A]">{run.status === "fulfilled_source" ? "Bandingkan sumber yang tersedia" : "Penawaran vendor melalui WhatsApp"}</h2>
      {run.status !== "fulfilled_source" && run.transport !== "whatsapp" && !comparison && <><p className="text-sm text-gray-600">Stok gudang asal kurang. Gunakan tombol di bawah untuk menghubungi nomor pengujian yang diizinkan. Balasan vendor digunakan untuk melengkapi stok, harga, ongkir, pajak, dan waktu tiba.</p>{<button className={primary} disabled={busy} onClick={() => void startWhatsApp(true)}>Kirim RFQ WhatsApp pengujian</button>}</>}
      {run.transport === "whatsapp" && (automationError === "whatsapp" || incompleteWhatsAppStart) && <button className={secondary} disabled={busy} onClick={() => void startWhatsApp(true)}>Coba lengkapi pengiriman penawaran</button>}
      {!foodRun && (run.transport === "whatsapp" || run.status === "fulfilled_source") && <><p className="text-sm text-gray-600">{run.transport === "whatsapp" ? "Balasan dan perbandingan diperbarui otomatis. Stok kosong dibedakan dari vendor yang belum menjawab. Setelah penawaran lengkap, sistem menawar maksimal satu kali per vendor bila target harga memungkinkan. Penawaran belum lengkap atau masih dinegosiasikan belum dapat dipilih." : "Stok gudang asal memenuhi kebutuhan. Siapkan perbandingan tanpa menghubungi vendor."}</p><button className={primary} disabled={busy || live.refreshing || !config || !!confirm} onClick={prepare}>{busy ? "Menyiapkan…" : waitingForVendors ? "Bandingkan data yang tersedia" : comparison ? "Perbarui perbandingan" : "Siapkan perbandingan"}</button></>}
    </section>}
    {foodRun && !selected && <section className={`${card} space-y-4`}><h2 className="text-lg font-bold">Benchmark biaya produksi hilang</h2><p className="text-sm">NSK SS-E-2054: 3.332 unit $ publikasi/jam. ISO mata uang dan tahun harga tidak diketahui. Nilai rupiah merupakan estimasi skenario.</p><label className="block text-sm">Asumsi IDR per satu unit dolar publikasi<input className={field} value={mapping} onChange={e=>setMapping(e.target.value)}/></label><label className="flex gap-3 text-sm"><input type="checkbox" checked={benchmarkAck} onChange={e=>setBenchmarkAck(e.target.checked)}/>Saya memahami penerapan benchmark dan konversi ini adalah asumsi simulasi.</label><button className={primary} disabled={busy||live.refreshing||!benchmarkAck||!!confirm} onClick={prepare}>Hitung / perbarui perbandingan</button></section>}
    {comparison && <SourceComparison comparison={comparison} config={config} selected={selected} busy={busy || live.refreshing || comparisonStale} onChoose={openConfirmation} />}
    {run && <WarehouseStock run={run} config={config} />}
    {run && run.vendors.length > 0 && <section className={`${card} overflow-x-auto`}><h2 className="text-lg font-bold">{run.transport === "whatsapp" ? "Penawaran WhatsApp nyata" : "Penawaran simulator"}</h2><p className="mb-4 mt-1 text-sm text-slate-600">{run.transport === "whatsapp" ? "Hanya penawaran dari balasan vendor yang ditampilkan. Maksimal satu penawaran harga per vendor." : "Data sintetis, maksimal satu penawaran harga per vendor. Tidak ada pesan WhatsApp nyata."}</p>{run.negotiation && <p className="mb-4 rounded-xl bg-[#F8E8B6]/60 p-3 text-sm text-[#0F274A]">Negosiasi putaran {run.negotiation.round}: total acuan {money(run.negotiation.best_total)} → target total {money(run.negotiation.target_total)} (10% lebih rendah). Target harga per buah memperhitungkan biaya selain barang dari masing-masing vendor.</p>}<table className="w-full min-w-[850px] text-left text-sm"><thead className="border-b border-gray-200 bg-[#EAECEF] text-xs uppercase text-gray-700"><tr>{["Vendor", "Hasil", "Stok", "Harga awal / buah", "Harga akhir / buah", "Negosiasi", "Tawaran harga"].map(h => <th key={h} className="px-3 py-3">{h}</th>)}</tr></thead><tbody>{run.vendors.map(v => <tr key={v.vendor_id} className="border-b border-slate-100"><td className="px-3 py-4 font-semibold">{v.vendor_id}</td><td className="px-3 py-4">{run.transport === "whatsapp" && v.outcome === "pending" ? "Menunggu penawaran lengkap" : label(v.outcome)}</td><td className="px-3 py-4">{v.outcome === "no_stock" ? "0" : stockQuantity(v.quote?.qty_available)}</td><td className="px-3 py-4">{money(v.initial_quote?.unit_price)}</td><td className="px-3 py-4">{money(v.quote?.unit_price)}</td><td className="px-3 py-4"><p>{negotiationStatus(run, v)}</p>{run.negotiation?.vendors.find(plan => plan.vendor_id === v.vendor_id)?.target_unit_price && <p className="mt-1 text-xs text-gray-500">Target {money(run.negotiation.vendors.find(plan => plan.vendor_id === v.vendor_id)?.target_unit_price)} / buah</p>}</td><td className="px-3 py-4">{v.counteroffers_used} / 1</td></tr>)}</tbody></table></section>}
    {run?.transport === "whatsapp" && <section className={`${card} space-y-4`}><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-bold">Percakapan vendor</h2></div>{conversations.length ? <WhatsAppConversationsView conversations={conversations} recipients={whatsApp?.recipients} /> : <p className="text-sm text-gray-500">Memuat percakapan untuk pencarian ini…</p>}</section>}
    {confirm && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-5"><section role="dialog" aria-modal="true" aria-labelledby="decision-heading" className="w-full max-w-md space-y-4 rounded-3xl border border-gray-100 bg-white p-6 shadow-2xl sm:p-8"><h2 id="decision-heading" className="text-xl font-bold text-[#0F274A]">{confirm.source_kind === "vendor" ? "Setujui Purchase Order demo?" : "Pilih sumber gudang?"}</h2><p className="text-sm">Pilih {sourceName(confirm, config)} untuk seluruh {session?.quantity} buah. Sistem akan memeriksa kembali stok atau validitas penawaran.</p><p className="text-sm text-gray-600">{confirm.source_kind === "vendor" ? "Persetujuan ini membuat PO demo PT PartPilot dari harga dan jumlah yang disetujui. Dokumen tidak dikirim otomatis melalui email atau WhatsApp." : "Permintaan mutasi dicatat untuk demo. Tidak ada pemberitahuan nyata kepada staf, perpindahan stok, atau PO."}</p><ErrorNotice message={error} />{confirmationStale && <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-900">Data telah berubah atau keputusan sudah tercatat. Tinjau kembali sebelum melanjutkan.</p>}<div className="flex justify-end gap-3"><button className={secondary} disabled={busy} onClick={closeConfirmation}>{confirmationStale ? "Tutup & perbarui" : "Batal"}</button><button className={primary} disabled={busy || confirmationStale} onClick={choose}>{busy ? "Menyimpan…" : confirm.source_kind === "vendor" ? "Konfirmasi PO demo" : "Konfirmasi pilihan gudang"}</button></div></section></div>}
    {warehouseConfirmation && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-5"><section role="dialog" aria-modal="true" aria-labelledby="warehouse-confirmation" className="w-full max-w-md space-y-4 rounded-3xl border border-gray-100 bg-white p-6 text-center shadow-2xl sm:p-8"><CheckCircle2 className="mx-auto h-12 w-12 rounded-2xl bg-emerald-100 p-3 text-emerald-700" /><h2 id="warehouse-confirmation" className="text-xl font-bold text-[#0F274A]">Request mutasi berhasil dicatat</h2><p className="text-sm">{warehouseConfirmation} dipilih untuk {session?.quantity} buah. Permintaan ini dicatat sebagai demo. Tidak ada pemberitahuan nyata kepada staf, perpindahan stok, atau PO.</p><button autoFocus className={primary} onClick={() => setWarehouseConfirmation("")}>Selesai</button></section></div>}
  </DemoShell>;
}
function DecisionRoute() { const sessionId = useSearchParams().get("session"); return <DecisionContent key={sessionId || "no-session"} sessionId={sessionId} />; }
export default function Decision() { return <Suspense fallback={<p className="p-8">Memuat perbandingan…</p>}><DecisionRoute /></Suspense>; }
