export type DemoConfig = {
  generation: number;
  context: Record<string, string>;
  warehouses: { id: string; name: string }[];
  assumptions: Record<string, unknown>;
  scenarios: { id: string; label: string; description: string; quantity: string; warehouse_id: string }[];
};
export type Session = {
  id: string; version: number; state: string; description: string; quantity: string;
  warehouse_id: string; urgency: string; identified_item_code?: string;
  questions: { id: string; key: string; prompt: string; options?: string[] }[];
  facts: { key: string; value: string }[];
  conflicts?: { key?: string; message?: string }[];
  error?: { code: string; message: string; retriable: boolean };
  run_id?: string; comparison_id?: string; decision?: { option_id: string };
};
export type Quote = {
  unit_price: string | null; qty_available: string; shipping_amount: string | null;
  tax_amount: string | null; delivered_eta: string | null; valid_until: string;
  processing_hours: string | null;
};
export type Scope = { warehouse_id: string; status: string; item_code?: string; available_qty?: string; actual_qty?: string; reserved_qty?: string; evidence?: { item_name?: string }[] };
export type Run = {
  id: string; version: number; status: string; quantity: string;
  identity: { brand: string; base: string; suffix: string };
  availability: { origin: Scope; alternatives: Scope[]; complete: boolean };
  vendors: { vendor_id: string; outcome: string; counteroffers_used: number; quote: Quote | null; initial_quote: Quote | null; eligible: boolean }[];
  decision?: { option_id: string };
};
export type Option = {
  option_id: string; source_kind: string; source_id: string; item_code?: string;
  quote: Quote | null; reasons?: string[]; valid_until?: string;
  assumptions?: { schedule?: { stages?: { kind: string; end: string }[] } };
  economics?: { sourcing_total?: string; unrecoverable_lost_contribution?: string;
    incremental_disruption_total?: string; future_relevant_option_total?: string };
};
export type Comparison = {
  id: string; version: number; eligible_complete_options: Option[]; unrankable_options: Option[];
  unexpired_option_ids: string[]; coverage_complete: boolean;
};
export type Orders = { generation: number; items: Session[] };

let activeGeneration: number | undefined;
export async function api<T>(path: string, body?: unknown, key?: string): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    method: body === undefined ? "GET" : "POST",
    cache: "no-store", credentials: "same-origin",
    headers: { ...(body !== undefined ? { "Content-Type": "application/json", "X-PartPilot-Request": "demo", "X-PartPilot-Generation": String(activeGeneration ?? "") } : {}), ...(key ? { "Idempotency-Key": key } : {}) },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    signal: AbortSignal.timeout(60000),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.error?.message || `Permintaan gagal (${response.status}). Muat ulang lalu coba lagi.`);
  if (path === "/demo/config" && typeof data?.generation === "number") activeGeneration = data.generation;
  return data as T;
}
export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Permintaan gagal. Coba lagi.";
}
export function money(value: string | null | undefined): string {
  return value == null ? "Belum diketahui" : new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 2 }).format(Number(value));
}
export function dateTime(value: string | null | undefined): string {
  return value ? new Date(value).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" }) : "Belum diketahui";
}
export function stockQuantity(value: string | null | undefined): string {
  return value == null ? "Belum diketahui" : new Intl.NumberFormat("id-ID", { maximumFractionDigits: 3 }).format(Number(value));
}
const labels: Record<string, string> = {
  draft: "Draf", queued: "Antre identifikasi", processing: "AI mengidentifikasi", awaiting_clarification: "Perlu klarifikasi",
  identified: "Identitas ditemukan", no_match: "Belum ada kecocokan", knowledge_unavailable: "Aturan penamaan belum tersedia",
  needs_review: "Perlu pemeriksaan manusia", failed: "Proses gagal", sufficient: "Stok cukup", insufficient: "Stok kurang",
  insufficient_stock: "Stok kurang", no_response: "Tidak merespons — stok belum diketahui", no_stock: "Stok kosong",
  negotiation_refused: "Menolak nego — harga awal berlaku", revised_quote: "Membalas harga baru", quoted: "Penawaran diterima",
  pending: "Belum dihubungi", no_valid_quote: "Belum ada penawaran valid", missing_recovery_assumptions: "Asumsi pemulihan belum lengkap",
  expired_quote: "Penawaran kedaluwarsa", not_found: "Barang belum ditemukan", not_searched: "Tidak perlu pencarian lanjutan",
  fulfilled_source: "Stok asal mencukupi", sourcing: "Mencari sumber alternatif",
};
export function label(value: string): string { return labels[value] || value.replaceAll("_", " "); }
