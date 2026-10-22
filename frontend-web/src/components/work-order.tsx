"use client";
import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { LoaderCircle, CheckCircle2, Sparkles, Search, Save, Minus, Plus } from "lucide-react";
import { api, errorMessage, label, type DemoConfig, type Session } from "@/lib/partpilot";
import { accent, card, DemoShell, ErrorNotice, field, primary, secondary } from "./demo-shell";

function WorkOrderContent() {
  const params = useSearchParams();
  const router = useRouter();
  const sessionId = params.get("session");
  const [config, setConfig] = useState<DemoConfig | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [description, setDescription] = useState("");
  const [warehouse, setWarehouse] = useState("SYN-WH-01");
  const [quantity, setQuantity] = useState("6");
  const [urgency, setUrgency] = useState("Medium");
  const [notes, setNotes] = useState("");
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState<{ id: string; submitted: boolean } | null>(null);
  const [failedDraftId, setFailedDraftId] = useState<string | null>(null);
  const submission = useRef<{ body: string; key: string } | null>(null);
  useEffect(() => { let active = true; api<DemoConfig>("/demo/config").then(v => { if (active) setConfig(v); }).catch(e => { if (active) setError(errorMessage(e)); }); return () => { active = false; }; }, []);
  useEffect(() => {
    if (!sessionId) return;
    let active = true; let timer: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try {
        const next = await api<Session>(`/work-orders/${encodeURIComponent(sessionId!)}`);
        if (!active) return;
        setSession(previous => previous?.id === next.id && previous.version > next.version ? previous : next);
        if (["queued", "processing"].includes(next.state)) timer = setTimeout(poll, 1500);
      } catch (e) { if (active) { setError(errorMessage(e)); timer = setTimeout(poll, 5000); } }
    }
    void poll();
    return () => { active = false; clearTimeout(timer); };
  }, [sessionId, session?.version]);

  async function create(submit: boolean) {
    if (!config || busy || success) return;
    if (!description.trim() || !/^\d+$/.test(quantity) || Number(quantity) < 1) { setError("Isi deskripsi dan jumlah bearing minimal 1 buah."); return; }
    setBusy(true); setError("");
    let createdId: string | undefined;
    try {
      const body = { ...config.context, warehouse_id: warehouse, description: description.trim(), quantity, urgency, notes };
      const serialized = JSON.stringify(body);
      if (submission.current?.body !== serialized) submission.current = { body: serialized, key: crypto.randomUUID() };
      const draft = await api<Session>("/work-orders", body, submission.current.key);
      createdId = draft.id; setSession(draft);
      if (submit) setSession(await api<Session>(`/work-orders/${draft.id}/submit`, { expected_version: draft.version }, `submit-${draft.id}-${draft.version}`));
      setFailedDraftId(null); setSuccess({ id: draft.id, submitted: submit });
    } catch (e) { setError(errorMessage(e)); if (createdId) setFailedDraftId(createdId); }
    finally { setBusy(false); }
  }
  async function continueSession(action: "submit" | "answers" | "retry") {
    if (!session || busy) return;
    const relevant = session.questions || [];
    if (action === "answers" && relevant.some(q => !answers[q.id]?.trim())) { setError("Jawab semua pertanyaan sebelum mengirim klarifikasi."); return; }
    setBusy(true); setError("");
    try {
      const body = { expected_version: session.version, ...(action === "answers" ? { answers: relevant.map(q => ({ question_id: q.id, answer: answers[q.id].trim() })) } : {}) };
      const serialized = JSON.stringify(body);
      if (submission.current?.body !== serialized) submission.current = { body: serialized, key: crypto.randomUUID() };
      setSession(await api<Session>(`/work-orders/${session.id}/${action}`, body, submission.current.key));
      setAnswers({});
      if (action === "submit") setSuccess({ id: session.id, submitted: true });
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  const shown = sessionId ? session : null;
  return <DemoShell title="Form work order" config={config} compact>
    <ErrorNotice message={error} />
    {failedDraftId && <p className="rounded-xl bg-amber-50 p-4 text-sm text-amber-900">Draf sudah tersimpan, tetapi pengajuan untuk identifikasi belum berhasil dikonfirmasi. <Link className="font-semibold underline" href={`/technician/clarification/?session=${encodeURIComponent(failedDraftId)}`}>Buka draf dan periksa status</Link>.</p>}
    {!config && !error && <p role="status">Memuat data demo…</p>}
    {sessionId && !shown && !error && <p role="status">Memuat work order…</p>}
    {!sessionId && config && <>
      <form className="space-y-6 rounded-2xl border border-gray-200/90 bg-white p-6 shadow-xs sm:p-8" onSubmit={e => { e.preventDefault(); void create(true); }}>
        <div className="flex items-start gap-3"><Sparkles className="mt-0.5 shrink-0 text-[#0F274A]" size={24} /><div><h2 className="text-lg font-bold text-[#0F274A]">Deskripsi masalah & kebutuhan suku cadang</h2><p className="mt-1 text-sm text-gray-500">Ceritakan kondisi mesin dan ciri bearing yang terlihat. Kode barang tidak wajib.</p></div></div>
        <label className="block text-sm font-semibold">Apa masalahnya dan seperti apa bearing yang dibutuhkan?<textarea className={`${field} min-h-[120px] resize-y p-4`} rows={4} value={description} onChange={e => setDescription(e.target.value)} placeholder="Bearing conveyor berisik. Diameter luarnya terukur 30 mm, ciri lainnya belum diperiksa." required maxLength={8000} disabled={busy} /><span className="mt-2 block text-xs font-normal leading-relaxed text-gray-500">Ceritakan ciri yang sudah terlihat. Bila informasi belum cukup, agen akan menanyakan merek, ukuran lainnya, dan penutup bearing.</span></label>
        <details className="space-y-3"><summary className="cursor-pointer text-xs font-semibold text-[#17375E]">Saran cepat: contoh kebutuhan bearing</summary><div className="flex flex-wrap gap-2">{config.scenarios.map(s => <button type="button" key={s.id} className="cursor-pointer rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs font-medium hover:bg-gray-100" disabled={busy} onClick={() => { setDescription(s.description); setQuantity(String(s.quantity)); setWarehouse(s.warehouse_id); setNotes(""); setError(""); }}>{s.label}</button>)}</div></details>
        <div className="grid gap-5 md:grid-cols-2 sm:gap-6">
          <label className="text-sm font-semibold">Mesin<input className={field} value="Conveyor • Lini perakitan AC (demo)" readOnly /></label>
          <div><label htmlFor="quantity" className="text-sm font-semibold">Jumlah (buah) <span className="text-red-500">*</span></label><div className="mt-2 flex items-center gap-2"><button type="button" className="flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-xl border border-gray-200 bg-white hover:bg-gray-50 disabled:opacity-50" disabled={busy || Number(quantity) <= 1} aria-label="Kurangi jumlah" onClick={() => setQuantity(String(Math.max(1, Number(quantity) - 1)))}><Minus size={16} /></button><input id="quantity" type="number" min="1" max="999999" step="1" value={quantity} onChange={e => setQuantity(e.target.value)} className="h-11 min-w-0 flex-1 rounded-xl border border-gray-200 bg-white text-center text-sm font-semibold outline-none focus:ring-2 focus:ring-[#0F274A]" required disabled={busy} /><button type="button" className="flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-xl border border-gray-200 bg-white hover:bg-gray-50 disabled:opacity-50" disabled={busy || Number(quantity) >= 999999} aria-label="Tambah jumlah" onClick={() => setQuantity(String(Math.min(999999, Number(quantity) + 1)))}><Plus size={16} /></button></div></div>
        </div>
        <label className="block text-sm font-semibold">Gudang asal<select value={warehouse} onChange={e => setWarehouse(e.target.value)} className={field} disabled={busy}>{config.warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}</select></label>
        <fieldset><legend className="mb-2 text-sm font-semibold">Urgensi</legend><div className="grid grid-cols-2 gap-3 sm:grid-cols-4">{["Low", "Medium", "High", "Critical"].map(value => <button type="button" key={value} disabled={busy} aria-pressed={urgency === value} onClick={() => setUrgency(value)} className={`h-11 cursor-pointer rounded-xl border text-sm font-medium transition-colors ${urgency === value ? "border-[#0F274A] bg-[#0F274A] text-white shadow-xs" : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50"}`}>{value}</button>)}</div></fieldset>
        <label className="block text-sm font-semibold">Catatan tambahan<input value={notes} onChange={e => setNotes(e.target.value)} placeholder="Misalnya: mesin berhenti, seal rusak, tulisan pada bearing tidak terbaca" className={field} maxLength={2000} disabled={busy} /></label>
        <div className="flex flex-wrap justify-end gap-3 pt-2"><button className={accent} disabled={busy}>{busy ? "Mengirim…" : "Cari bearing"}<Search size={16} /></button><button type="button" className={primary} onClick={() => create(false)} disabled={busy}>Simpan draf<Save size={16} className="ml-2" /></button></div>
      </form>
    </>}
    {shown && <>
      <section className={`${card} space-y-4`}>
        {shown.state === "awaiting_clarification" && <div className="flex justify-center pb-2 pt-1"><div className="inline-flex items-center gap-3 rounded-2xl border border-[#F3D58C] bg-[#F8E8B6] px-5 py-3 shadow-2xs"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 border-[#8C6D23] text-xs font-bold text-[#8C6D23]">AI</span><p className="text-sm font-semibold">Lengkapi ciri bearing agar agen dapat menemukan barang yang tepat.</p></div></div>}
        <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs text-slate-500 break-all">WO {shown.id}</p><h2 className="mt-2 text-lg font-bold">{shown.description}</h2><p className="mt-2 text-sm text-slate-600">{shown.quantity} buah • {shown.warehouse_id} • {shown.urgency}</p></div><span className="rounded-full bg-blue-50 px-3 py-2 text-sm font-medium">{label(shown.state)}</span></div>
        {["queued", "processing"].includes(shown.state) && <p role="status" className="flex items-center gap-3 rounded-xl bg-slate-50 p-4 text-sm"><LoaderCircle className="animate-spin" size={20} />Identifikasi sedang berjalan. Halaman ini akan memperbarui hasil otomatis; aman untuk dimuat ulang.</p>}
        {shown.facts?.length > 0 && <dl className="flex flex-wrap gap-3">{shown.facts.map((f, i) => <div key={`${f.key}-${i}`} className="rounded-xl bg-slate-50 px-4 py-2"><dt className="text-xs text-slate-500">{label(f.key)}</dt><dd className="font-semibold">{f.value}</dd></div>)}</dl>}
        {shown.error && <ErrorNotice message={`${shown.error.code}: ${shown.error.message}`} />}
        {shown.state === "draft" && <button className={primary} disabled={busy} onClick={() => continueSession("submit")}>Kirim draf untuk identifikasi</button>}
        {shown.state === "awaiting_clarification" && <form onSubmit={e => { e.preventDefault(); void continueSession("answers"); }} className="space-y-4 border-t border-slate-200 pt-5">
          <h3 className="font-semibold">Lengkapi informasi bearing</h3><p className="text-sm text-slate-600">Jawab dari hasil pengamatan: ukuran, merek, serta penutup karet atau logam. Kode tidak wajib; jangan menebak jika cirinya belum terlihat.</p>
          {(shown.questions || []).map(q => <label key={q.id} className="block text-sm font-medium">{q.prompt}<input className={field} value={answers[q.id] || ""} onChange={e => setAnswers(a => ({ ...a, [q.id]: e.target.value }))} required maxLength={2000} disabled={busy} />{q.options?.length ? <span className="mt-1 block text-xs text-slate-500">Contoh pilihan: {q.options.join(", ")}</span> : null}</label>)}
          <div className="flex justify-end border-t border-gray-100 pt-4"><button className={accent} disabled={busy || !(shown.questions || []).length}>{busy ? "Mengirim…" : "Kirim klarifikasi"}</button></div>
        </form>}
        {shown.state === "identified" && <div className="space-y-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4"><p className="flex items-center gap-2 font-semibold"><CheckCircle2 size={20} />Identitas cocok: {shown.identified_item_code}</p><p className="text-sm">Identitas ditemukan. Lanjutkan pencarian stok dan perbandingan sumber; perbaikan mesin belum dinyatakan selesai.</p><Link href={`/manager/decision/?session=${shown.id}`} className={primary}>Lihat stok dan bandingkan sumber</Link></div>}
        {shown.state === "failed" && shown.error?.retriable && <button className={primary} onClick={() => continueSession("retry")} disabled={busy}>Coba identifikasi lagi</button>}
        {["no_match", "needs_review", "knowledge_unavailable"].includes(shown.state) && <p className="rounded-xl bg-amber-50 p-4 text-sm">WO ini belum dapat dipakai untuk pengadaan. Periksa ukuran, jenis penutup, dan merek yang terlihat. Bila datanya sudah benar, minta pemeriksaan katalog sebelum membuat WO yang dikoreksi.</p>}
      </section>
      <div className="flex gap-3"><Link className={secondary} href="/technician/">Buat WO baru</Link><Link className={secondary} href="/manager/">Lihat semua WO</Link><button className={secondary} onClick={() => window.location.reload()} disabled={busy}>Muat ulang hasil</button></div>
    </>}
    {success && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-5"><section role="dialog" aria-modal="true" aria-labelledby="wo-success-heading" className="w-full max-w-md space-y-4 rounded-3xl border border-gray-100 bg-white p-6 text-center shadow-2xl sm:p-8"><CheckCircle2 className="mx-auto h-12 w-12 rounded-2xl bg-emerald-100 p-3 text-emerald-700" /><h2 id="wo-success-heading" className="text-xl font-bold text-[#0F274A]">{success.submitted ? "Work order berhasil diajukan" : "Draf work order berhasil disimpan"}</h2><p className="text-sm text-gray-600">{success.submitted ? "Work order sudah diterima untuk proses identifikasi. Jika informasi barang belum cukup, sistem akan meminta klarifikasi sebelum stok dan perbandingan dapat dibuka." : "Draf tersimpan. Lanjutkan draf dan ajukan untuk memulai identifikasi barang."}</p><div className="flex flex-col gap-3"><Link className={primary} href="/manager/">Ke Meja manajer</Link><button autoFocus className={secondary} onClick={() => { const id = success.id; setSuccess(null); router.replace(`/technician/clarification/?session=${encodeURIComponent(id)}`); }}>{success.submitted ? "Lanjutkan klarifikasi" : "Lanjutkan draf"}</button></div></section></div>}
  </DemoShell>;
}
export default function WorkOrder() { return <Suspense fallback={<p className="p-8">Memuat work order…</p>}><WorkOrderContent /></Suspense>; }
