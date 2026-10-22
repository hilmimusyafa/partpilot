"use client";
import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { LoaderCircle, CheckCircle2, Sparkles, Search, Save } from "lucide-react";
import { api, errorMessage, label, type DemoConfig, type Session } from "@/lib/partpilot";
import { card, DemoShell, ErrorNotice, field, primary, secondary } from "./demo-shell";

function WorkOrderContent() {
  const params = useSearchParams();
  const router = useRouter();
  const sessionId = params.get("session");
  const [config, setConfig] = useState<DemoConfig | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [description, setDescription] = useState("");
  const [warehouse, setWarehouse] = useState("SYN-WH-01");
  const [quantity, setQuantity] = useState("1");
  const [urgency, setUrgency] = useState("Medium");
  const [notes, setNotes] = useState("");
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submission = useRef<{ body: string; key: string } | null>(null);
  useEffect(() => { let active = true; api<DemoConfig>("/demo/config").then(v => { if (active) setConfig(v); }).catch(e => { if (active) setError(errorMessage(e)); }); return () => { active = false; }; }, []);
  useEffect(() => {
    if (!sessionId) return;
    let active = true; let timer: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try {
        const next = await api<Session>(`/work-orders/${encodeURIComponent(sessionId!)}`);
        if (!active) return;
        setSession(next);
        if (["queued", "processing"].includes(next.state)) timer = setTimeout(poll, 1500);
      } catch (e) { if (active) setError(errorMessage(e)); }
    }
    void poll();
    return () => { active = false; clearTimeout(timer); };
  }, [sessionId, session?.version]);

  async function create(submit: boolean) {
    if (!config || busy) return;
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
    } catch (e) { setError(errorMessage(e)); } finally {
      setBusy(false);
      if (createdId) router.replace(`/technician/clarification/?session=${encodeURIComponent(createdId)}`);
    }
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
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  const shown = sessionId ? session : null;
  return <DemoShell title={sessionId ? "Identifikasi work order" : "Form work order"} config={config} compact>
    <ErrorNotice message={error} />
    {!config && !error && <p role="status">Memuat data demo…</p>}
    {sessionId && !shown && !error && <p role="status">Memuat work order…</p>}
    {!sessionId && config && <>
      <details className={`${card} space-y-3`}><summary className="cursor-pointer font-semibold text-[#0F274A]">Contoh kebutuhan bearing</summary><p className="text-sm text-slate-600">Pilih contoh untuk mengisi form, atau jelaskan sendiri kondisi yang Anda lihat.</p>
        <div className="flex flex-wrap gap-2">{config.scenarios.map(s => <button key={s.id} className={secondary} disabled={busy} onClick={() => { setDescription(s.description); setQuantity(String(s.quantity)); setWarehouse(s.warehouse_id); setNotes(""); setError(""); }}>{s.label}</button>)}</div>
      </details>
      <form className={`${card} space-y-5`} onSubmit={e => { e.preventDefault(); void create(true); }}>
        <div className="flex items-start gap-3"><Sparkles className="mt-0.5 shrink-0 text-[#0F274A]" size={24} /><div><h2 className="text-lg font-bold text-[#0F274A]">Deskripsi masalah & kebutuhan suku cadang</h2><p className="mt-1 text-sm text-gray-500">Ceritakan kondisi mesin dan ciri bearing yang terlihat. Kode barang tidak wajib.</p></div></div>
        <p className="rounded-xl bg-blue-50/70 px-4 py-3 text-sm text-[#17375E]">Conveyor • Lini perakitan AC (demo)</p>
        <label className="block text-sm font-semibold">Apa masalahnya dan seperti apa bearing yang dibutuhkan?<textarea className={field} rows={4} value={description} onChange={e => setDescription(e.target.value)} placeholder="Bearing conveyor berisik. Diameter dalam 10 mm, luar 30 mm, lebar 9 mm. Penutup karet di kedua sisi, merek NTN terlihat pada bearing." required maxLength={8000} disabled={busy} /><span className="mt-2 block text-xs font-normal leading-relaxed text-gray-500">Tuliskan ukuran yang terukur (diameter dalam × luar × lebar), penutup karet atau logam, dan merek jika terbaca. Bila belum tahu, ceritakan yang terlihat; sistem akan meminta klarifikasi.</span></label>
        <div className="grid gap-5 sm:grid-cols-3">
          <label className="text-sm font-semibold">Gudang asal<select value={warehouse} onChange={e => setWarehouse(e.target.value)} className={field} disabled={busy}>{config.warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}</select></label>
          <label className="text-sm font-semibold">Jumlah (buah)<input type="number" min="1" max="999999" step="1" value={quantity} onChange={e => setQuantity(e.target.value)} className={field} required disabled={busy} /></label>
          <label className="text-sm font-semibold">Urgensi<select value={urgency} onChange={e => setUrgency(e.target.value)} className={field} disabled={busy}>{["Low", "Medium", "High", "Critical"].map(v => <option key={v}>{v}</option>)}</select></label>
        </div>
        <label className="block text-sm font-semibold">Catatan tambahan<input value={notes} onChange={e => setNotes(e.target.value)} placeholder="Misalnya: mesin berhenti, seal rusak, tulisan pada bearing tidak terbaca" className={field} maxLength={2000} disabled={busy} /></label>
        <div className="flex flex-wrap justify-end gap-3 border-t border-gray-100 pt-5"><button type="button" className={secondary} onClick={() => create(false)} disabled={busy}><Save size={16} className="mr-2" />Simpan draf</button><button className={primary} disabled={busy}><Search size={16} className="mr-2" />{busy ? "Mengirim…" : "Cari bearing"}</button></div>
      </form>
    </>}
    {shown && <>
      <section className={`${card} space-y-4`}>
        <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs text-slate-500 break-all">WO {shown.id}</p><h2 className="mt-2 text-lg font-bold">{shown.description}</h2><p className="mt-2 text-sm text-slate-600">{shown.quantity} buah • {shown.warehouse_id} • {shown.urgency}</p></div><span className="rounded-full bg-blue-50 px-3 py-2 text-sm font-medium">{label(shown.state)}</span></div>
        {["queued", "processing"].includes(shown.state) && <p role="status" className="flex items-center gap-3 rounded-xl bg-slate-50 p-4 text-sm"><LoaderCircle className="animate-spin" size={20} />Identifikasi sedang berjalan. Halaman ini akan memperbarui hasil otomatis; aman untuk dimuat ulang.</p>}
        {shown.facts?.length > 0 && <dl className="flex flex-wrap gap-3">{shown.facts.map((f, i) => <div key={`${f.key}-${i}`} className="rounded-xl bg-slate-50 px-4 py-2"><dt className="text-xs text-slate-500">{f.key}</dt><dd className="font-semibold">{f.value}</dd></div>)}</dl>}
        {shown.error && <ErrorNotice message={`${shown.error.code}: ${shown.error.message}`} />}
        {shown.state === "draft" && <button className={primary} disabled={busy} onClick={() => continueSession("submit")}>Kirim draf untuk identifikasi</button>}
        {shown.state === "awaiting_clarification" && <form onSubmit={e => { e.preventDefault(); void continueSession("answers"); }} className="space-y-4 border-t border-slate-200 pt-5">
          <h3 className="font-semibold">Lengkapi informasi bearing</h3><p className="text-sm text-slate-600">Jawab dari hasil pengamatan: ukuran, merek, serta penutup karet atau logam. Kode tidak wajib; jangan menebak jika cirinya belum terlihat.</p>
          {(shown.questions || []).map(q => <label key={q.id} className="block text-sm font-medium">{q.prompt}<input className={field} value={answers[q.id] || ""} onChange={e => setAnswers(a => ({ ...a, [q.id]: e.target.value }))} required maxLength={2000} disabled={busy} />{q.options?.length ? <span className="mt-1 block text-xs text-slate-500">Contoh pilihan: {q.options.join(", ")}</span> : null}</label>)}
          <button className={primary} disabled={busy || !(shown.questions || []).length}>{busy ? "Mengirim…" : "Kirim klarifikasi"}</button>
        </form>}
        {shown.state === "identified" && <div className="space-y-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4"><p className="flex items-center gap-2 font-semibold"><CheckCircle2 size={20} />Identitas cocok: {shown.identified_item_code}</p><p className="text-sm">Identitas ditemukan. Lanjutkan pencarian stok dan perbandingan sumber; perbaikan mesin belum dinyatakan selesai.</p><Link href={`/manager/decision/?session=${shown.id}`} className={primary}>Lihat stok dan bandingkan sumber</Link></div>}
        {shown.state === "failed" && shown.error?.retriable && <button className={primary} onClick={() => continueSession("retry")} disabled={busy}>Coba identifikasi lagi</button>}
        {["no_match", "needs_review", "knowledge_unavailable"].includes(shown.state) && <p className="rounded-xl bg-amber-50 p-4 text-sm">WO ini belum dapat dipakai untuk pengadaan. Periksa ukuran, jenis penutup, dan merek yang terlihat. Bila datanya sudah benar, minta pemeriksaan katalog sebelum membuat WO yang dikoreksi.</p>}
      </section>
      <div className="flex gap-3"><Link className={secondary} href="/technician/">Buat WO baru</Link><Link className={secondary} href="/manager/">Lihat semua WO</Link><button className={secondary} onClick={() => window.location.reload()} disabled={busy}>Muat ulang hasil</button></div>
    </>}
  </DemoShell>;
}
export default function WorkOrder() { return <Suspense fallback={<p className="p-8">Memuat work order…</p>}><WorkOrderContent /></Suspense>; }
