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
  transport?: "simulator" | "whatsapp";
  identity: { brand: string; base: string; suffix: string };
  availability: { origin: Scope; alternatives: Scope[]; complete: boolean };
  vendors: { vendor_id: string; outcome: string; counteroffers_used: number; quote: Quote | null; initial_quote: Quote | null; eligible: boolean; ineligible_reasons?: string[] }[];
  decision?: { option_id: string };
  negotiation?: { policy: string; round: number; best_option_id: string | null; best_total: string | null; target_total: string | null; basis_at: string | null; vendors: { vendor_id: string; status: "planned" | "skipped"; reason: string | null; target_unit_price: string | null }[] };
};
export type PurchaseOrder = { id: string; number: string; supplier?: { id: string; name: string }; quantity?: string; unit_price?: string; shipping_amount?: string; tax_amount?: string; total?: string };
export type PurchaseOrderResult = { purchase_order: PurchaseOrder | null };
export type Option = {
  option_id: string; source_kind: string; source_id: string; item_code?: string;
  quote: Quote | null; reasons?: string[]; valid_until?: string;
  assumptions?: { schedule?: { stages?: { kind: string; end: string }[] } };
  economics?: { sourcing_total?: string; unrecoverable_lost_contribution?: string;
    incremental_disruption_total?: string; future_relevant_option_total?: string; future_relevant_option_total_unrounded?: string };
};
function decimalParts(value: string | undefined) {
  const match = value?.match(/^([+-]?)(?:(\d+)(?:\.(\d*))?|\.(\d+))(?:[eE]([+-]?\d+))?$/);
  if (!match) return null;
  const fraction = match[3] ?? match[4] ?? "";
  const digits = ((match[2] ?? "") + fraction).replace(/^0+/, "");
  const exponent = Number(match[5] ?? 0) + digits.length - fraction.length;
  if (!Number.isSafeInteger(exponent)) return null;
  return { sign: !digits ? 0 : match[1] === "-" ? -1 : 1, digits, exponent };
}
function lexicalCompare(a: string, b: string): number { return a < b ? -1 : a > b ? 1 : 0; }
/** Match the backend Decimal ordering without rounding or floating-point conversion. */
export function compareOptionCosts(a: Option, b: Option): number {
  const left = decimalParts(a.economics?.future_relevant_option_total_unrounded ?? a.economics?.future_relevant_option_total);
  const right = decimalParts(b.economics?.future_relevant_option_total_unrounded ?? b.economics?.future_relevant_option_total);
  let costOrder = 0;
  if (!left || !right) costOrder = left ? -1 : right ? 1 : 0;
  else if (left.sign !== right.sign) costOrder = Math.sign(left.sign - right.sign);
  else if (left.sign !== 0) {
    const length = Math.max(left.digits.length, right.digits.length);
    costOrder = left.sign * (Math.sign(left.exponent - right.exponent) || lexicalCompare(left.digits.padEnd(length, "0"), right.digits.padEnd(length, "0")));
  }
  return costOrder || lexicalCompare(a.source_kind, b.source_kind) || lexicalCompare(a.source_id, b.source_id);
}
export type Comparison = {
  id: string; version: number; eligible_complete_options: Option[]; unrankable_options: Option[];
  unexpired_option_ids: string[]; coverage_complete: boolean;
};
export type Orders = { generation: number; items: Session[] };
export type WhatsAppStatus = {
  connection: string; qr_data_url: string | null; enabled: boolean;
  can_start: boolean; blocked_reason?: string | null;
  recipients: { id: string; label: string; registered: boolean | null }[];
};
export type WhatsAppConversation = {
  id: string; run_id: string; vendor_id: string; status: string;
  fields: Record<string, unknown>; missing_fields: string[];
  messages: { direction: string; text: string; created_at: string; status?: string }[];
  counteroffers_used: number; followups_used: number;
};
export type WhatsAppConversations = { conversations: WhatsAppConversation[] };

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
  category: "Kategori", quantity: "Jumlah", brand: "Merek", base: "Kode dasar", suffix: "Akhiran kode", item_code: "Kode barang", item_name: "Nama barang",
  dimensions: "Ukuran", seal_type: "Jenis penutup", inner_diameter_mm: "Diameter dalam (mm)", outer_diameter_mm: "Diameter luar (mm)", width_mm: "Lebar (mm)",
  draft: "Draf", queued: "Antre identifikasi", processing: "AI mengidentifikasi", awaiting_clarification: "Perlu klarifikasi",
  identified: "Identitas ditemukan", no_match: "Belum ada kecocokan", knowledge_unavailable: "Aturan penamaan belum tersedia",
  needs_review: "Perlu pemeriksaan manusia", failed: "Proses gagal", sufficient: "Stok cukup", insufficient: "Stok kurang",
  insufficient_stock: "Stok kurang", no_response: "Tidak merespons — stok belum diketahui", no_stock: "Stok kosong",
  negotiation_refused: "Menolak nego — harga awal berlaku", revised_quote: "Membalas harga baru", quoted: "Penawaran diterima",
  already_negotiated: "satu putaran negosiasi sudah digunakan", non_item_cost_exceeds_target: "biaya selain barang sudah melampaui target", already_below_target: "harga vendor sudah memenuhi target",
  benchmark_expired: "penawaran acuan sudah kedaluwarsa",
  quote_changed_before_negotiation: "penawaran berubah sebelum negosiasi dikirim",
  pending: "Belum dihubungi", no_valid_quote: "Belum ada penawaran valid", missing_recovery_assumptions: "Asumsi pemulihan belum lengkap",
  expired_quote: "Penawaran kedaluwarsa", not_found: "Barang belum ditemukan", not_searched: "Tidak perlu pencarian lanjutan",
  fulfilled_source: "Stok asal mencukupi", sourcing: "Mencari sumber alternatif",
  connected: "Terhubung", open: "Terhubung", disconnected: "Belum terhubung", connecting: "Menghubungkan", close: "Koneksi terputus",
  awaiting_reply: "Menunggu balasan vendor", awaiting_response: "Menunggu balasan vendor", awaiting_fields: "Menunggu kelengkapan penawaran",
  ready: "Penawaran lengkap", sent: "Pesan terkirim", sending: "Mengirim pesan", qr: "Pindai QR untuk menghubungkan",
  uncertain: "Pengiriman belum dapat dipastikan; tidak diulang otomatis", cancelled: "Pengiriman dibatalkan", received: "Balasan diterima", processed: "Balasan diproses",
  waiting: "Menunggu balasan vendor", partial: "Penawaran belum lengkap", closed: "Percakapan ditutup", negotiation_pending: "Menunggu jawaban negosiasi", identity: "Identitas bearing",
  unit_price: "Harga per buah", qty_available: "Stok tersedia", shipping_amount: "Ongkir", tax_amount: "Pajak", delivered_eta: "Estimasi tiba", valid_until: "Berlaku sampai", processing_hours: "Waktu proses (jam)",
};
export function label(value: string): string { return labels[value] || value.replaceAll("_", " "); }
