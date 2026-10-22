import { dateTime, label, type WhatsAppConversation } from "@/lib/partpilot";

export function WhatsAppConversationsView({ conversations, recipients = [] }: {
  conversations: WhatsAppConversation[];
  recipients?: { id: string; label: string }[];
}) {
  return <div className="space-y-4">{conversations.map(conversation => {
    const name = recipients.find(recipient => recipient.id === conversation.vendor_id)?.label || conversation.vendor_id;
    const inbound = conversation.messages.filter(message => message.direction === "in" || message.direction === "inbound");
    const latest = inbound.at(-1);
    return <article key={conversation.id} id={`conversation-${conversation.id}`} className="rounded-xl border border-gray-200 bg-white p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="font-bold text-[#0F274A]">{name}</h3><p className="mt-1 text-xs text-gray-500">Pencarian {conversation.run_id.slice(0, 8)} • WhatsApp nyata</p></div><span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-[#17375E]">{label(conversation.status)}</span></div>
      <p className="mt-3 text-sm text-gray-600">{latest ? `Balasan terakhir: ${latest.text}` : "Belum ada balasan vendor. Harga, stok, dan waktu kirim belum dapat disimpulkan."}</p>
      {conversation.status === "closed" && <p className="mt-2 rounded-lg bg-amber-50 p-3 text-xs text-amber-900">Percakapan ini sudah ditutup. Pesan lama atau balasan terlambat adalah riwayat; bukan penawaran aktif untuk keputusan baru.</p>}
      <p className="mt-2 text-xs text-gray-500">{inbound.length} balasan • {conversation.followups_used} tindak lanjut • {conversation.counteroffers_used} / 1 counteroffer</p>
      {Object.keys(conversation.fields).length > 0 && <dl className="mt-4 grid gap-3 rounded-xl bg-gray-50 p-4 sm:grid-cols-2">{Object.entries(conversation.fields).map(([key, value]) => <div key={key}><dt className="text-xs text-gray-500">{label(key)}</dt><dd className="mt-1 break-words text-sm font-medium">{value == null ? "Belum diketahui" : typeof value === "object" ? JSON.stringify(value) : String(value)}</dd></div>)}</dl>}
      {conversation.missing_fields.length > 0 && <p className="mt-3 text-xs text-amber-800">Belum lengkap: {conversation.missing_fields.map(label).join(", ")}. Belum dapat dipakai sebagai penawaran lengkap.</p>}
      <details className="mt-4 border-t border-gray-100 pt-3"><summary className="cursor-pointer text-sm font-semibold text-[#17375E]">Lihat percakapan ({conversation.messages.length} pesan)</summary>
        <ol className="mt-4 space-y-3">{conversation.messages.map((message, index) => {
          const received = message.direction === "in" || message.direction === "inbound";
          return <li key={`${message.created_at}-${index}`} className={`max-w-[90%] rounded-xl p-3 ${received ? "border border-gray-200 bg-gray-50" : "ml-auto bg-blue-50 text-[#17375E]"}`}><p className="text-xs font-semibold">{received ? name : "PartPilot"}</p><p className="mt-1 whitespace-pre-wrap break-words text-sm">{message.text}</p><p className="mt-2 text-xs text-gray-500">{dateTime(message.created_at)}{message.status ? ` • ${message.status === "queued" ? "Antre kirim" : label(message.status)}` : ""}</p></li>;
        })}</ol>
        {conversation.messages.length === 0 && <p className="mt-3 text-sm text-gray-500">Belum ada pesan tercatat.</p>}
      </details>
    </article>;
  })}</div>;
}
