"use client";
import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { MessageCircle, QrCode, RefreshCw } from "lucide-react";
import { api, errorMessage, label, type DemoConfig, type WhatsAppConversations, type WhatsAppStatus } from "@/lib/partpilot";
import { card, DemoShell, ErrorNotice, primary, secondary } from "./demo-shell";
import { WhatsAppConversationsView } from "./whatsapp-conversations";

export default function WhatsApp() {
  const [config, setConfig] = useState<DemoConfig | null>(null);
  const [status, setStatus] = useState<WhatsAppStatus | null>(null);
  const [data, setData] = useState<WhatsAppConversations | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function load() {
      try {
        const [configuration, connection, conversations] = await Promise.all([
          api<DemoConfig>("/demo/config"), api<WhatsAppStatus>("/whatsapp/status"), api<WhatsAppConversations>("/whatsapp/conversations"),
        ]);
        if (!active) return;
        setConfig(configuration); setStatus(connection); setData(conversations); setError("");
      } catch (e) {
        if (active) { setError(errorMessage(e)); setStatus(null); }
      } finally { if (active) timer = setTimeout(load, 5000); }
    }
    void load();
    return () => { active = false; clearTimeout(timer); };
  }, [refresh]);

  async function connect() {
    if (busy || !config || !status?.enabled) return;
    setBusy(true); setError("");
    try { await api("/whatsapp/connect", {}); setRefresh(value => value + 1); }
    catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  const connected = status?.connection === "connected" || status?.connection === "open";
  // The QR is received through the authenticated API and kept only in this mounted page.
  const qr = status?.qr_data_url?.startsWith("data:image/png;base64,") ? status.qr_data_url : null;
  return <DemoShell title="WhatsApp vendor" config={config}>
    <ErrorNotice message={error} />
    <div className="flex flex-wrap items-center justify-between gap-3"><p className="text-sm text-gray-500">Status dan percakapan diperbarui setiap 5 detik.</p><button className={secondary} onClick={() => setRefresh(value => value + 1)} disabled={busy}><RefreshCw size={16} className="mr-2" />Muat ulang</button></div>
    <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
      <section className={`${card} space-y-4`}><div className="flex items-center gap-3"><QrCode className="text-[#17375E]" /><h2 className="text-lg font-bold text-[#0F274A]">Hubungkan WhatsApp</h2></div>
        <p role="status" className={`rounded-xl p-3 text-sm font-semibold ${connected ? "bg-emerald-50 text-emerald-800" : "bg-blue-50 text-[#17375E]"}`}>{status ? label(status.connection) : error ? "Status belum dapat dimuat" : "Memuat status koneksi…"}</p>
        {qr && !connected ? <div className="space-y-3"><Image src={qr} alt="QR pribadi untuk menghubungkan akun WhatsApp" width={280} height={280} unoptimized className="mx-auto h-auto max-w-full rounded-xl border border-gray-200 bg-white p-3" /><p className="text-sm text-gray-600">Buka WhatsApp di ponsel → Perangkat tertaut → Tautkan perangkat. QR diperbarui otomatis ketika berubah.</p><p className="text-xs text-gray-500">QR bersifat pribadi. Jangan bagikan tangkapan layarnya.</p></div> : !connected && <p className="text-sm text-gray-600">Mulai koneksi untuk menampilkan QR. Menghubungkan akun belum mengirim pesan ke vendor.</p>}
        {connected ? <p className="text-sm text-gray-600">Akun terhubung. Pesan permintaan penawaran dimulai dari work order yang sudah teridentifikasi.</p> : <button className={primary} disabled={busy || !config || !status?.enabled} onClick={connect}>{busy ? "Menghubungkan…" : qr ? "Perbarui koneksi" : "Tampilkan QR WhatsApp"}</button>}
        {status && !status.enabled && <p className="text-sm text-amber-800">Koneksi WhatsApp belum diaktifkan di server.</p>}
        {status && !status.can_start && <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-900">{status.blocked_reason || "Pengiriman belum siap. Lengkapi pengaturan vendor sebelum mengirim permintaan."}</p>}
        <div className="border-t border-gray-100 pt-4"><h3 className="text-sm font-semibold">Vendor yang dikonfigurasi</h3><ul className="mt-3 space-y-2 text-sm">{status?.recipients.map(recipient => <li key={recipient.id} className="flex flex-wrap justify-between gap-2"><span>{recipient.label}</span><span className="text-xs text-gray-500">{recipient.registered === true ? "Terdaftar di WhatsApp" : recipient.registered === false ? "Tidak terdaftar" : "Belum diperiksa"}</span></li>)}</ul>{status?.recipients.length === 0 && <p className="mt-2 text-sm text-gray-500">Belum ada vendor yang dikonfigurasi.</p>}</div>
      </section>
      <section className={`${card} space-y-4`}><div className="flex items-center gap-3"><MessageCircle className="text-[#17375E]" /><h2 className="text-lg font-bold text-[#0F274A]">Percakapan vendor nyata</h2></div><p className="text-sm text-gray-500">Balasan, kelengkapan penawaran, dan batas negosiasi berasal dari percakapan yang tercatat.</p>
        {!data && !error && <p role="status" className="text-sm">Memuat percakapan…</p>}
        {data?.conversations.length === 0 && <div className="rounded-xl bg-gray-50 p-6 text-center"><p className="font-semibold text-[#0F274A]">Belum ada percakapan</p><p className="mt-2 text-sm text-gray-500">Buka WO yang sudah teridentifikasi lalu pilih “Hubungi vendor via WhatsApp”.</p><Link href="/manager/" className={`${primary} mt-4`}>Buka meja manajer</Link></div>}
        {data && <WhatsAppConversationsView conversations={data.conversations} recipients={status?.recipients} />}
      </section>
    </div>
  </DemoShell>;
}
