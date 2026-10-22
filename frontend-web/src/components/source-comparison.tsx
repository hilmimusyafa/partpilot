"use client";
import { Calculator, CheckCircle2, FileCheck, Download } from "lucide-react";
import { compareOptionCosts, dateTime, label, money, sourceName, stockQuantity, type DemoConfig, type Comparison, type Option, type PurchaseOrder } from "@/lib/partpilot";
import { card, primary, secondary } from "./demo-shell";

export function rankedOptions(comparison: Comparison): Option[] {
  return [...comparison.eligible_complete_options].sort(compareOptionCosts);
}

export function SourceRecommendation({ comparison, config, selected, busy, onChoose }: {
  comparison: Comparison; config?: DemoConfig | null; selected: string; busy: boolean; onChoose: (option: Option) => void;
}) {
  const best = rankedOptions(comparison).find(option => comparison.unexpired_option_ids.includes(option.option_id));
  if (!best) return null;
  return <section className="rounded-2xl border border-[#ECD394] bg-[#F6E5B4] p-6 shadow-xs sm:p-7 space-y-4" aria-labelledby="recommendation-heading">
    <div className="flex items-center gap-3"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 border-[#8C6D23] text-[#8C6D23]"><Calculator size={14} aria-hidden="true" /></span><h2 id="recommendation-heading" className="text-xs font-extrabold uppercase tracking-wider text-[#0D5C75] sm:text-sm">Rekomendasi berdasarkan biaya</h2></div>
    <div><h3 className="text-lg font-bold text-gray-900">{sourceName(best, config)}</h3><ul className="mt-2 list-disc space-y-1 pl-4 text-sm leading-relaxed"><li>Total relevan terendah dari opsi lengkap yang masih berlaku: <strong>{money(best.economics?.future_relevant_option_total)}</strong>.</li><li>Stok tersedia {stockQuantity(best.quote?.qty_available)} buah. Estimasi tiba {dateTime(best.quote?.delivered_eta)}.</li><li>Perbandingan mencakup biaya barang, ongkir, pajak, pemulihan, dan kontribusi produksi yang hilang.</li></ul></div>
    {!comparison.coverage_complete && <p className="text-xs text-amber-900">Sebagian sumber belum memiliki data lengkap. Rekomendasi dapat berubah setelah data tersedia.</p>}
    <button className={primary} disabled={busy || !!selected} onClick={() => onChoose(best)}>{selected ? "Keputusan sudah tercatat" : `Pilih ${sourceName(best, config)}`}</button>
  </section>;
}

export function PurchaseOrderCard({ purchaseOrder, error, busy, onRetry }: { purchaseOrder: PurchaseOrder | null; error: string; busy: boolean; onRetry: () => void }) {
  return <section className={`${card} space-y-3`} aria-label="Purchase Order demo">
    <h2 className="flex items-center gap-2 text-lg font-bold text-[#0F274A]"><FileCheck size={22} />Purchase Order • PT PartPilot</h2>
    {purchaseOrder ? <><p className="break-all font-semibold">{purchaseOrder.number}</p><p className="text-sm text-gray-600">PO demo dibuat dari penawaran yang disetujui manajer. Dokumen tidak dikirim otomatis melalui email atau WhatsApp.</p>{purchaseOrder.total != null && <dl className="grid gap-3 rounded-xl bg-gray-50 p-4 text-sm sm:grid-cols-3"><div><dt className="text-xs text-gray-500">Pemasok</dt><dd className="mt-1 font-semibold">{purchaseOrder.supplier?.name || purchaseOrder.supplier?.id || "Lihat dokumen PO"}</dd></div><div><dt className="text-xs text-gray-500">Jumlah yang disetujui</dt><dd className="mt-1 font-semibold">{stockQuantity(purchaseOrder.quantity)} buah × {money(purchaseOrder.unit_price)}</dd></div><div><dt className="text-xs text-gray-500">Total PO (barang, ongkir, pajak)</dt><dd className="mt-1 font-bold">{money(purchaseOrder.total)}</dd></div></dl>}<a className={primary} href={`/api/v1/demo/purchase-orders/${encodeURIComponent(purchaseOrder.id)}/pdf`} download><Download size={16} className="mr-2" />Unduh PO (PDF)</a></> : <><p role={error ? "alert" : "status"} className={`text-sm ${error ? "text-red-800" : "text-gray-600"}`}>{error || (busy ? "Memuat dokumen PO…" : "Dokumen PO belum tersedia. Periksa kembali untuk mengambil dokumen keputusan ini.")}</p><button className={secondary} disabled={busy} onClick={onRetry}>{busy ? "Memuat…" : "Muat ulang PO"}</button></>}
  </section>;
}

export function SourceComparison({ comparison, config, selected, busy, onChoose }: {
  comparison: Comparison; config?: DemoConfig | null; selected: string; busy: boolean; onChoose: (option: Option) => void;
}) {
  const ranked = rankedOptions(comparison);
  const ranks = new Map(ranked.map((option, index) => [option.option_id, index + 1]));
  return <div className="space-y-5">
    <div><h2 className="text-lg font-bold text-[#0F274A]">Biaya total sampai produksi pulih</h2><p className="mt-1 text-sm text-gray-600">Peringkat global mengurutkan total relevan dari terendah ke tertinggi. Gudang dan vendor ditampilkan terpisah; biaya pemulihan dan kehilangan kontribusi tidak masuk tagihan vendor.</p></div>
    {selected && <p role="status" className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold"><CheckCircle2 size={20} />Pilihan tercatat: {selected}. Tidak ada mutasi stok atau pengiriman pesanan otomatis.</p>}
    {ranked.length === 0 && <p className="rounded-xl bg-amber-50 p-4 text-sm">Belum ada opsi lengkap yang memenuhi kebutuhan. Manajer belum bisa memilih sumber.</p>}
    {[{ kind: "warehouse", title: "Sumber gudang" }, { kind: "vendor", title: "Penawaran vendor" }].map(group => {
      const options = ranked.filter(option => option.source_kind === group.kind);
      const unavailable = comparison.unrankable_options.filter(option => option.source_kind === group.kind);
      return <section key={group.kind} className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-xs" aria-label={group.title}>
        <div className="flex items-center justify-between gap-3 p-5"><h3 className="font-bold text-[#0F274A]">{group.title}</h3><span className="text-xs text-gray-500">{options.length} opsi lengkap • total menaik</span></div>
        <p className="px-5 pb-3 text-xs text-gray-500 sm:hidden">Geser tabel untuk melihat seluruh biaya dan tombol pilihan →</p>
        <div className="overflow-x-auto"><table className="w-full min-w-[1100px] border-collapse text-left text-xs sm:text-sm">
          <caption className="sr-only">{group.title}, diurutkan berdasarkan total relevan</caption>
          <thead><tr className="border-b border-gray-200 bg-[#EAECEF] text-[11px] font-bold uppercase tracking-wider text-gray-700">{["Peringkat / sumber", "Stok", "Harga / buah", "Ongkir / pajak", "Barang + ongkir + pajak", "Kehilangan kontribusi", "Pemulihan", "Total relevan", "Tindakan"].map(title => <th scope="col" key={title} className="px-3 py-3.5">{title}</th>)}</tr></thead>
          <tbody className="divide-y divide-gray-100">{options.map(option => {
            const available = comparison.unexpired_option_ids.includes(option.option_id);
            return <tr key={option.option_id} className={selected === option.option_id ? "bg-emerald-50" : ranks.get(option.option_id) === 1 ? "bg-blue-50/20" : "hover:bg-gray-50/80"}>
              <td className="px-4 py-4"><span className="mb-2 inline-block rounded-md bg-[#0F274A] px-2 py-1 text-[11px] font-bold text-white">#{ranks.get(option.option_id)} global</span><p className="font-semibold text-gray-900">{sourceName(option, config)}</p>{option.source_kind === "warehouse" && <p className="mt-1 text-xs text-gray-500">{option.source_id}<br />{config?.warehouses.find(warehouse => warehouse.id === option.source_id)?.address || "Alamat demo belum tersedia"}</p>}<p className="mt-1 text-xs text-gray-500">{option.item_code || "Sesuai identitas bearing"}</p><details className="mt-2 text-xs"><summary className="cursor-pointer font-medium text-[#17375E]">Waktu & validitas</summary><p className="mt-2 max-w-56 leading-relaxed">Tiba: {dateTime(option.quote?.delivered_eta)}<br />Pulih: {dateTime(option.assumptions?.schedule?.stages?.find(stage => stage.kind === "restart")?.end)}<br />Berlaku sampai: {dateTime(option.valid_until)}</p></details></td>
              <td className="px-3 py-4">{stockQuantity(option.quote?.qty_available)}</td><td className="px-3 py-4">{money(option.quote?.unit_price)}</td><td className="px-3 py-4"><p>{money(option.quote?.shipping_amount)}</p><p className="mt-1 text-xs text-gray-500">Pajak {money(option.quote?.tax_amount)}</p></td><td className="px-3 py-4">{money(option.economics?.sourcing_total)}</td><td className="px-3 py-4"><span className="rounded-md bg-amber-100/70 px-2 py-1 font-medium text-amber-800">{money(option.economics?.unrecoverable_lost_contribution)}</span></td><td className="px-3 py-4">{money(option.economics?.incremental_disruption_total)}</td><td className="px-3 py-4 font-bold text-gray-900">{money(option.economics?.future_relevant_option_total)}</td>
              <td className="px-4 py-4"><button className="w-28 cursor-pointer rounded-md bg-[#0F274A] px-3 py-2 text-xs font-semibold text-white shadow-2xs hover:bg-[#152e55] disabled:cursor-not-allowed disabled:opacity-50" disabled={busy || !!selected || !available} onClick={() => onChoose(option)}>{selected === option.option_id ? "Sudah dipilih" : !available ? "Kedaluwarsa" : group.kind === "warehouse" ? "Pilih gudang" : "Setujui PO"}</button></td>
            </tr>;
          })}</tbody>
        </table></div>
        {!options.length && <p className="px-5 py-6 text-sm text-gray-500">Belum ada {group.title.toLowerCase()} yang lengkap dan memenuhi kebutuhan.</p>}
        {unavailable.length > 0 && <div className="space-y-2 border-t border-gray-100 bg-gray-50 p-5"><h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500">Belum dapat dipilih</h4>{unavailable.map(option => <p key={option.option_id} className="text-sm"><strong>{sourceName(option, config)}</strong> — {(option.reasons || []).map(label).join("; ") || "Data belum lengkap"}</p>)}</div>}
      </section>;
    })}
  </div>;
}
