import { label, stockQuantity, warehouseName, type DemoConfig, type Run } from "@/lib/partpilot";
import { card } from "./demo-shell";

export function WarehouseStock({ run, config }: { run: Run; config: DemoConfig | null }) {
  const scopes = [run.availability.origin, ...run.availability.alternatives];
  const warehouseIds = [...new Set([...(config?.warehouses.map(warehouse => warehouse.id) || []), ...scopes.map(scope => scope.warehouse_id)])];
  return <section className={`${card} space-y-4`} aria-labelledby="warehouse-stock-heading">
    <div><h2 id="warehouse-stock-heading" className="text-lg font-bold">Stok barang yang sama di setiap gudang</h2><p className="mt-1 text-sm text-slate-600">Barang yang dicari: <strong>{run.identity.brand} {run.identity.base}{run.identity.suffix}</strong>, sebanyak <strong>{stockQuantity(run.quantity)} buah</strong>. Nama dan kode pada setiap gudang dapat berbeda; sistem mencocokkan identitas bearing pada label dan aturan penamaan tiap gudang (merek, model, dan jenis penutup).</p><p className="mt-2 text-xs text-slate-500">Stok fisik = barang yang ada di gudang. Sudah dialokasikan = bagian yang disiapkan untuk kebutuhan lain. Bisa dipakai = stok fisik dikurangi alokasi tersebut. Kekurangan dihitung terhadap seluruh kebutuhan WO ini.</p></div>
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{warehouseIds.map(id => {
      const scope = scopes.find(item => item.warehouse_id === id);
      const warehouse = config?.warehouses.find(item => item.id === id);
      const shortfall = scope?.available_qty == null ? undefined : String(Math.max(0, Number(run.quantity) - Number(scope.available_qty)));
      return <article key={id} className="space-y-3 rounded-xl border border-slate-200 p-4" aria-label={warehouseName(id, config)}>
        <div><h3 className="font-semibold text-[#0F274A]">{warehouseName(id, config)}</h3><p className="mt-1 text-xs text-gray-500">{id}{id === run.availability.origin.warehouse_id ? " • Gudang asal" : ""}</p><p className="mt-2 text-xs leading-relaxed text-gray-500">{warehouse?.address || "Alamat demo belum tersedia"}</p></div>
        <div className="rounded-lg bg-slate-50 p-3 text-xs"><p className="font-semibold">Nama di gudang</p><p className="mt-1">{scope?.evidence?.[0]?.item_name || "Nama barang belum ditemukan"}</p><p className="mt-2 text-gray-500">Kode di gudang: <span className="break-all font-medium text-gray-700">{scope?.item_code || "Belum ditemukan"}</span></p></div>
        <dl className="grid grid-cols-2 gap-x-2 gap-y-2 text-xs"><dt>Stok fisik</dt><dd className="text-right">{stockQuantity(scope?.actual_qty)}</dd><dt>Sudah dialokasikan</dt><dd className="text-right">{stockQuantity(scope?.reserved_qty)}</dd><dt className="font-semibold">Bisa dipakai</dt><dd className="text-right font-bold text-[#0F274A]">{stockQuantity(scope?.available_qty)}</dd><dt>Kebutuhan WO</dt><dd className="text-right">{stockQuantity(run.quantity)}</dd><dt>Kekurangan</dt><dd className="text-right font-semibold">{stockQuantity(shortfall)}</dd></dl>
        <p className={`text-xs font-medium ${scope?.status === "sufficient" ? "text-emerald-700" : "text-amber-800"}`}>{scope ? label(scope.status) : "Data gudang belum diperiksa"} • satuan buah</p>
      </article>;
    })}</div>
    {!run.availability.complete && <p className="text-sm text-amber-800">Sebagian data atau identitas barang belum dapat dipastikan. Ini bukan bukti stok kosong.</p>}
  </section>;
}
