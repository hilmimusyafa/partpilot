"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, errorMessage, type DemoConfig, type Session, type Run, type Comparison, type Option, type WhatsAppConversations, type WhatsAppConversation, type PurchaseOrderResult } from "@/lib/partpilot";
import { DemoShell, ErrorNotice, card, field, primary, secondary } from "@/components/demo-shell";
import { WarehouseStock } from "@/components/warehouse-stock";
import { SourceComparison, SourceRecommendation, PurchaseOrderCard } from "@/components/source-comparison";
import { WhatsAppConversationsView } from "@/components/whatsapp-conversations";

type Evidence = { id: string; kind: string; title: string; facts: Record<string, unknown>; source_refs: { url: string; locator: string; source_id: string }[] };
type Assessment = { id: string; status: string; model_metadata: Record<string, unknown>; result: {
  diagnosis?: { status: string; summary: string; hypotheses: { cause: string; verification: string; evidence_ids: string[] }[] };
  recommendations?: { action: string; evidence_ids: string[] }[]; follow_up?: string[]; missing_prerequisites?: string[];
  exact_part_proposal?: {sku:string}|null; engineering_candidate?: {sku:string}|null;
  evidence_refs?: {evidence_id:string}[]; limitations?: string[]; error?: string; message?: string;
}; tool_trace: { sequence: number; tool_name: string; status: string; evidence_ids: string[]; duration_ms: number }[] };
type FoodConfig = { context: Record<string,string>; symptoms: string; observed_part_code: string; quantity: string; currency_mapping_note: string; suggested_demo_currency_mapping: string };

export default function MaintenanceWorkspace() {
  const [config,setConfig]=useState<DemoConfig|null>(null), [food,setFood]=useState<FoodConfig|null>(null);
  const [evidence,setEvidence]=useState<Evidence[]>([]), [assessment,setAssessment]=useState<Assessment|null>(null);
  const [symptoms,setSymptoms]=useState(""), [part,setPart]=useState("RHP PSF20CR"), [quantity,setQuantity]=useState("2");
  const [technician,setTechnician]=useState(""), [confirmed,setConfirmed]=useState(false);
  const [session,setSession]=useState<Session|null>(null), [run,setRun]=useState<Run|null>(null), [comparison,setComparison]=useState<Comparison|null>(null);
  const [kind,setKind]=useState<"exact"|"candidate">("exact"), [reviewed,setReviewed]=useState(false), [reviewer,setReviewer]=useState("");
  const [checks,setChecks]=useState([false,false,false]), [reviewNotes,setReviewNotes]=useState("");
  const [benchmarkAck,setBenchmarkAck]=useState(false),[mapping,setMapping]=useState("18000");
  const [chats,setChats]=useState<WhatsAppConversation[]>([]),[selected,setSelected]=useState(""),[confirmOption,setConfirmOption]=useState<Option|null>(null);
  const [po,setPo]=useState<PurchaseOrderResult|null>(null),[busy,setBusy]=useState(""),[error,setError]=useState("");
  useEffect(()=>{ Promise.all([api<DemoConfig>("/demo/config"),api<FoodConfig>("/food-demo/config"),api<{items:Evidence[]}>("/maintenance/evidence")])
    .then(([c,f,e])=>{setConfig(c);setFood(f);setSymptoms(f.symptoms);setEvidence(e.items);setMapping(f.suggested_demo_currency_mapping);})
    .catch(e=>setError(errorMessage(e))); },[]);
  useEffect(()=>{
    if(!session || ["identified","failed","needs_review","no_match","awaiting_clarification"].includes(session.state))return;
    const timer=setInterval(()=>{api<Session>(`/demo/orders/${session.id}`).then(setSession).catch(e=>setError(errorMessage(e)));},2000);
    return()=>clearInterval(timer);
  },[session]);
  useEffect(()=>{
    if(!run || run.transport!=="whatsapp" || selected)return;
    const timer=setInterval(()=>{Promise.all([api<Run>(`/demo/sourcing-runs/${run.id}`),api<WhatsAppConversations>(`/whatsapp/conversations?run_id=${run.id}`)])
      .then(([r,c])=>{setRun(r);setChats(c.conversations);}).catch(e=>setError(errorMessage(e)));},5000);
    return()=>clearInterval(timer);
  },[run,selected]);
  async function act(name:string,fn:()=>Promise<void>){if(busy)return;setBusy(name);setError("");try{await fn();}catch(e){setError(errorMessage(e));}finally{setBusy("");}}
  async function analyze(){if(!food)return;await act("AI membaca bukti…",async()=>{
    const a=await api<Assessment>("/maintenance/assess",{...food.context,symptoms,observed_part_code:part,quantity});
    setAssessment(a);setSession(null);setRun(null);setComparison(null);setReviewed(false);setSelected("");setPo(null);setConfirmed(false);
  });}
  async function makeWO(target:"exact"|"candidate"){if(!assessment)return;await act("Membuat WO…",async()=>{
    const s=await api<Session>(`/food-demo/assessments/${assessment.id}/work-orders`,{part_kind:target,observed_part_code:target==="exact"?part:"RHP PSF20/LP99",quantity,technician,inspected_and_confirmed:true},`food-wo-${crypto.randomUUID()}`);
    setKind(target);setSession(s);setRun(null);setComparison(null);setChats([]);
  });}
  async function review(){if(!assessment)return;await act("Mencatat review…",async()=>{
    await api(`/food-demo/assessments/${assessment.id}/engineering-review`,{reviewer,decision:"approved",interface_load_speed_checked:checks[0],temperature_duty_checked:checks[1],hygiene_approved:checks[2],notes:reviewNotes});setReviewed(true);
  });}
  async function stock(){if(!session)return;await act("Memeriksa gudang…",async()=>{setRun(await api<Run>("/demo/sourcing-runs",{session_id:session.id,expected_version:session.version},`food-source-${session.id}`));});}
  async function simulate(){if(!run)return;await act("Menjalankan penawaran simulasi…",async()=>{setRun(await api<Run>(`/demo/sourcing-runs/${run.id}/advance`,{}));setComparison(null);});}
  async function whatsapp(){if(!run)return;await act("Mengirim RFQ…",async()=>{
    const c=await api<WhatsAppConversations>(`/whatsapp/runs/${run.id}/start`,{});setChats(c.conversations);setRun(await api<Run>(`/demo/sourcing-runs/${run.id}`));setComparison(null);
  });}
  async function compare(){if(!run)return;await act("Menghitung biaya…",async()=>{
    const r=await api<Run>(`/demo/sourcing-runs/${run.id}`);setRun(r);
    setComparison(await api<Comparison>(`/food-demo/sourcing-runs/${run.id}/comparison`,{external_applicability_acknowledged:true,idr_per_published_currency_unit:mapping,conversion_assumption_acknowledged:true},`food-cost-${crypto.randomUUID()}`));
  });}
  async function choose(){if(!comparison||!confirmOption||!run)return;await act("Mencatat keputusan…",async()=>{
    await api(`/demo/comparisons/${comparison.id}/decision`,{expected_version:comparison.version,option_id:confirmOption.option_id,acknowledgment:"demo_only"},`food-decision-${comparison.id}-${confirmOption.option_id}`);
    setSelected(confirmOption.option_id);setConfirmOption(null);
    setPo(await api<PurchaseOrderResult>(`/demo/sourcing-runs/${run.id}/purchase-order`));
  });}
  const evidenceUsed=evidence.filter(e=>assessment?.result.evidence_refs?.some(r=>r.evidence_id===e.id)||assessment?.tool_trace.some(t=>t.evidence_ids.includes(e.id)));
  return <DemoShell title="Maintenance & Pengadaan" config={config}>
    <p className="max-w-4xl text-sm leading-6 text-slate-600">Conveyor bising setelah washdown. PartPilot mencari preseden OEM, menyarankan pemeriksaan dan part, lalu membandingkan gudang serta vendor berdasarkan waktu pemulihan dan biaya.</p>
    <ErrorNotice message={error}/>{busy&&<p role="status" className="rounded-xl bg-blue-50 p-4 text-sm">{busy}</p>}
    <section className={`${card} space-y-4`}><h2 className="text-lg font-bold">1. Gejala dan bukti teknisi</h2>
      <label className="block text-sm">Gejala<textarea className={field} rows={3} value={symptoms} onChange={e=>setSymptoms(e.target.value)}/></label>
      <div className="grid gap-4 sm:grid-cols-3"><label className="text-sm">Kode unit pada marking/BOM<input className={field} value={part} onChange={e=>setPart(e.target.value)}/></label><label className="text-sm">Jumlah hasil inspeksi<input className={field} type="number" min="1" value={quantity} onChange={e=>setQuantity(e.target.value)}/></label><label className="text-sm">Nama teknisi<input className={field} placeholder="Nama teknisi" value={technician} onChange={e=>setTechnician(e.target.value)}/></label></div>
      <p className="text-xs text-slate-500">Marking PSF20CR, dua unit, dan aset pada contoh ini merupakan skenario simulasi. Kode produknya nyata. Kasus OEM tidak menyebut SKU atau jumlah penggantian untuk aset ini.</p>
      <button className={primary} disabled={!!busy||!food} onClick={analyze}>Analisis dengan AI dan bukti OEM</button>
    </section>
    {assessment&&<section className={`${card} space-y-4`}><h2 className="text-lg font-bold">2. Analisis dan jejak penggunaan tools</h2>
      <p className="text-xs text-slate-500">Assessment {assessment.id} • {assessment.status}</p>
      {assessment.result.diagnosis?<><p className="font-medium">{assessment.result.diagnosis.summary}</p><p className="rounded-xl bg-amber-50 p-3 text-sm">Dugaan penyebab untuk diverifikasi melalui inspeksi. Tidak memprediksi umur bearing atau tanggal kerusakan.</p>
        <div className="grid gap-4 lg:grid-cols-2">{assessment.result.diagnosis.hypotheses.map((h,i)=><div key={i} className="rounded-xl border border-slate-200 p-4 text-sm"><strong>{h.cause}</strong><p className="mt-2">Pemeriksaan: {h.verification}</p><p className="mt-2 text-xs text-slate-500">{h.evidence_ids.join(" • ")}</p></div>)}</div>
        <ul className="list-disc space-y-2 pl-5 text-sm">{assessment.result.recommendations?.map((r,i)=><li key={i}>{r.action}</li>)}</ul>
        <details className="text-sm"><summary className="cursor-pointer font-semibold">Tindak lanjut maintenance dan batas bukti</summary><ul className="mt-3 list-disc space-y-2 pl-5">{[...(assessment.result.follow_up||[]),...(assessment.result.limitations||[])].map((s,i)=><li key={i}>{s}</li>)}</ul></details>
      </>:<pre className="whitespace-pre-wrap text-sm">{JSON.stringify(assessment.result,null,2)}</pre>}
      <ol className="space-y-2 rounded-xl bg-slate-50 p-4 text-sm">{assessment.tool_trace.map(t=><li key={t.sequence}><strong>{t.sequence}. {t.tool_name}</strong> • {t.status} • {t.duration_ms} ms<br/><span className="text-xs text-slate-500">{t.evidence_ids.join(" • ")}</span></li>)}</ol>
      <details className="text-sm"><summary className="cursor-pointer font-semibold">Dokumen yang dipakai dan sumber aslinya</summary><div className="mt-3 space-y-3">{evidenceUsed.map(e=><div key={e.id}><strong>{e.title}</strong><p className="text-xs">{e.kind} • Bukti eksternal, bukan histori aset sendiri.</p>{e.source_refs.map((s,i)=><a key={i} className="mr-3 inline-block text-blue-700 underline" href={s.url} target="_blank" rel="noreferrer">{s.source_id} · {typeof s.locator==='string'?s.locator:'Lihat sumber'}</a>)}</div>)}</div></details>
    </section>}
    {assessment?.status==="completed"&&<section className={`${card} space-y-4`}><h2 className="text-lg font-bold">3. Konfirmasi part dan work order</h2>
      <p className="text-sm"><strong>Exact: RHP PSF20CR</strong> — unit flange empat baut lengkap. <strong>Kandidat: RHP PSF20/LP99</strong> — perlu review engineering dan higiene.</p>
      <label className="flex items-start gap-3 text-sm"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>Saya sudah mengonfirmasi marking/BOM, jumlah, dan kebutuhan penggantian untuk skenario yang sedang dievaluasi.</label>
      <button className={primary} disabled={!!busy||!confirmed||technician.trim().length<2||!assessment.result.exact_part_proposal} onClick={()=>makeWO("exact")}>Buat / buka WO part exact</button>
      {assessment.result.engineering_candidate&&<details className="rounded-xl border border-slate-200 p-4"><summary className="cursor-pointer text-sm font-semibold">Review kandidat alternatif PSF20/LP99</summary><div className="mt-4 space-y-3 text-sm"><p>Dimensi antarmuka yang sama belum membuktikan kesetaraan. LP99: rentang −15…80°C, operasi kontinu di bawah 60°C. Bukti sertifikasi food contact/NSF H1 belum tersedia di paket sumber.</p>
        {["Antarmuka, beban, putaran dan fit diperiksa","Suhu dan duty cycle cocok","Tim higiene menyetujui penggunaan pada posisi ini"].map((label,i)=><label key={label} className="flex gap-3"><input type="checkbox" checked={checks[i]} onChange={e=>setChecks(checks.map((v,j)=>i===j?e.target.checked:v))}/>{label}</label>)}
        <label className="block">Reviewer<input className={field} value={reviewer} onChange={e=>setReviewer(e.target.value)}/></label><label className="block">Dasar keputusan (nyatakan jika hanya simulasi)<textarea className={field} value={reviewNotes} onChange={e=>setReviewNotes(e.target.value)}/></label>
        <button className={secondary} disabled={!!busy||!checks.every(Boolean)||reviewer.length<2||reviewNotes.length<10} onClick={review}>{reviewed?"Review sudah tercatat":"Catat persetujuan engineering"}</button>
        <button className={`${primary} ml-2`} disabled={!!busy||!reviewed||!confirmed||technician.trim().length<2} onClick={()=>makeWO("candidate")}>Cari sumber kandidat yang disetujui</button>
      </div></details>}
      {session&&<div className="rounded-xl bg-blue-50 p-4 text-sm"><p>WO {session.id} • {kind==="exact"?"PSF20CR":"PSF20/LP99"} • {session.state}</p>{session.state==="identified"?<button className={`${primary} mt-3`} disabled={!!busy} onClick={stock}>Cari gudang sendiri dan gudang lain</button>:<Link className="mt-2 inline-block underline" href={`/technician/clarification/?session=${session.id}`}>Buka detail / klarifikasi WO</Link>}</div>}
    </section>}
    {session&&<p className="text-sm"><Link className="font-semibold text-blue-700 underline" href={`/manager/decision/?session=${session.id}`}>Buka WO ini di meja manajer →</Link></p>}
    {run&&<><WarehouseStock run={run} config={config}/><section className={`${card} space-y-4`}><h2 className="text-lg font-bold">4. Vendor dan biaya sampai produksi pulih</h2><p className="text-sm">Pencarian ini untuk {run.identity.brand} {run.identity.base}{run.identity.suffix}. Stok, harga, ETA, instalasi 1 jam, restart 1 jam, dan tenaga perbaikan Rp250.000 adalah simulasi.</p>
      <div className="flex flex-wrap gap-3"><button className={secondary} disabled={!!busy||run.transport==="whatsapp"||!!selected} onClick={simulate}>Ambil penawaran vendor simulasi</button><button className={secondary} disabled={!!busy||run.transport==="whatsapp"||!!selected} onClick={whatsapp}>Kirim RFQ WhatsApp</button></div>
      <a className="inline-block text-sm text-blue-700 underline" href="/whatsapp/" target="_blank" rel="noreferrer">Status / koneksi WhatsApp (tab baru)</a>
      <p className="text-sm"><a href="https://www.nsk.com/am-en/tools-resources/bearings/aip/success-stories-overview/main-make-up-conveyor/" target="_blank" rel="noreferrer" className="text-blue-700 underline">NSK SS-E-2054</a> melaporkan biaya produksi hilang <strong>$3.332/jam</strong>. Mata uang ISO dan tahun harga tidak dipublikasikan. Ini benchmark eksternal, bukan kerugian terukur pabrik sendiri.</p>
      <label className="block max-w-sm text-sm">Asumsi IDR per satu unit dolar publikasi<input className={field} value={mapping} onChange={e=>setMapping(e.target.value)}/></label><p className="text-xs text-slate-500">{food?.currency_mapping_note}</p>
      <label className="flex items-start gap-3 text-sm"><input type="checkbox" checked={benchmarkAck} onChange={e=>setBenchmarkAck(e.target.checked)}/>Saya memahami penerapan benchmark dan konversi ini adalah asumsi skenario. Total rupiah yang dihasilkan merupakan estimasi simulasi.</label>
      <button className={primary} disabled={!!busy||!benchmarkAck||!!selected} onClick={compare}>Hitung / perbarui perbandingan</button>
      {run.transport==="whatsapp"&&<p className="text-sm text-slate-500">Balasan dibaca setiap 5 detik. Setelah penawaran atau negosiasi berubah, tekan perbarui perbandingan. WhatsApp tidak mengirim PO otomatis.</p>}
    </section></>}
    {!!chats.length&&<section className={card}><WhatsAppConversationsView conversations={chats}/></section>}
    {comparison&&<><SourceRecommendation comparison={comparison} config={config} selected={selected} busy={!!busy} onChoose={setConfirmOption}/><SourceComparison comparison={comparison} config={config} selected={selected} busy={!!busy} onChoose={setConfirmOption}/></>}
    {confirmOption&&<section className={`${card} space-y-4`} role="dialog" aria-label="Konfirmasi keputusan"><p>Pilih {confirmOption.source_id} untuk seluruh kebutuhan? Sistem memeriksa ulang stok dan penawaran. Satu assessment hanya boleh memiliki satu keputusan akhir, termasuk pilihan alternatif.</p><button className={primary} disabled={!!busy} onClick={choose}>Konfirmasi keputusan</button><button className={`${secondary} ml-3`} onClick={()=>setConfirmOption(null)}>Batal</button></section>}
    {po?.purchase_order&&<PurchaseOrderCard purchaseOrder={po.purchase_order} error="" busy={false} onRetry={()=>{}}/>}
  </DemoShell>;
}
