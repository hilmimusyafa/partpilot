"use client"

import * as React from "react"
import Link from "next/link"
import Image from "next/image"
import { useRouter } from "next/navigation"
import {
  RotateCcw,
  ArrowLeft,
  ArrowUpDown,
  Bell,
  CheckCircle2,
  Sparkles,
  MessageSquare,
  Check,
  X,
  FileCheck,
} from "lucide-react"

interface DecisionVendorRow {
  id: string
  vendor: string
  channel: string
  status: string
  unitPrice: string
  stock: number
  delivery: string
  shipping: string
  downtimeCost: string
  totalCost: string
  isRecommended?: boolean
}

const decisionRows: DecisionVendorRow[] = [
  {
    id: "v-1",
    vendor: "PT Hidrolik Cepat",
    channel: "(WhatsApp)",
    status: "Complete",
    unitPrice: "Rp4,200,000",
    stock: 1,
    delivery: "$600",
    shipping: "Pc",
    downtimeCost: "100",
    totalCost: "Rp4.35M",
    isRecommended: true,
  },
  {
    id: "v-2",
    vendor: "PT Express Teknik",
    channel: "(Email)",
    status: "Complete",
    unitPrice: "Rp5,100,000",
    stock: 1,
    delivery: "$160",
    shipping: "Pc",
    downtimeCost: "140",
    totalCost: "Rp5.1M",
    isRecommended: false,
  },
  {
    id: "v-3",
    vendor: "CV Seal Hemat",
    channel: "(WhatsApp)",
    status: "Complete",
    unitPrice: "Rp3,600,000",
    stock: 1,
    delivery: "$110",
    shipping: "Pc",
    downtimeCost: "300",
    totalCost: "Rp487.5M",
    isRecommended: false,
  },
]

export default function ManagerDecisionPage() {
  const router = useRouter()

  // Selected vendor state
  const [selectedVendor, setSelectedVendor] = React.useState<string>("PT Hidrolik Cepat")

  // Confirmation modal state
  const [confirmationModal, setConfirmationModal] = React.useState<{
    show: boolean
    vendor: string
    type: "approve" | "negotiate"
  }>({ show: false, vendor: "", type: "approve" })

  // Toast feedback state
  const [toastMessage, setToastMessage] = React.useState<string | null>(null)

  const showToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(null), 3500)
  }

  const handleSelectVendor = (vendorName: string) => {
    setSelectedVendor(vendorName)
    setConfirmationModal({ show: true, vendor: vendorName, type: "approve" })
  }

  const handleNegotiatePrice = (vendorName: string) => {
    setConfirmationModal({ show: true, vendor: vendorName, type: "negotiate" })
  }

  const handleConfirmApproval = () => {
    const vName = confirmationModal.vendor
    setConfirmationModal({ show: false, vendor: "", type: "approve" })
    showToast(`Purchase Order untuk ${vName} berhasil disetujui!`)
  }

  const handleConfirmNegotiation = () => {
    const vName = confirmationModal.vendor
    setConfirmationModal({ show: false, vendor: "", type: "negotiate" })
    showToast(`Pesan negosiasi AI telah dikirim ke ${vName} via WhatsApp!`)
  }

  return (
    <div className="min-h-screen bg-[#F1F3F6] text-gray-800 flex flex-col font-sans">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-5 right-5 z-60 flex items-center gap-2.5 px-4 py-3 rounded-xl shadow-lg border text-sm font-medium bg-white border-gray-200 text-gray-800 animate-in fade-in slide-in-from-top-3">
          <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Top Navbar matching Screenshot: LOGO | Order List | Bell | Avatar */}
      <header className="w-full bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          {/* Left: LOGO */}
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="flex items-center hover:opacity-85 transition-opacity"
            >
              <Image
                src="/logo.png"
                alt="PartPilot Logo"
                width={130}
                height={46}
                priority
                className="h-8 w-auto object-contain"
              />
            </Link>
          </div>

          {/* Right: Order List link | Notification Bell | User Avatar */}
          <div className="flex items-center gap-5 sm:gap-6">
            {/* Order List Link */}
            <Link
              href="/manager"
              className="text-sm font-bold text-[#0F274A] hover:underline cursor-pointer"
            >
              Order List
            </Link>

            {/* Notification Bell */}
            <button
              type="button"
              onClick={() => showToast("Perhatian: Rekomendasi vendor terbaik telah siap ditinjau!")}
              title="Notifications"
              className="relative p-1.5 rounded-xl hover:bg-gray-100 text-gray-600 transition-colors cursor-pointer"
            >
              <Bell className="w-5 h-5 stroke-[1.8]" />
              <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-amber-500 ring-2 ring-white" />
            </button>

            {/* User Profile Avatar */}
            <div className="w-9 h-9 rounded-full bg-[#E0F2FE] border border-[#BAE6FD] flex items-center justify-center text-[#0284C7] shadow-xs cursor-pointer hover:ring-2 hover:ring-[#38BDF8] transition-all">
              <svg
                className="w-5 h-5"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4c0-3.2-6.4-4.8-9.6-4.8z" />
              </svg>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 w-full max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-5">
        {/* Title Header & Actions Row */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-[#0F274A]">
              MEJA KEPUTUSAN
            </h1>
            <p className="text-xs sm:text-sm text-gray-500 mt-0.5">
              <Link href="/manager" className="hover:underline hover:text-gray-800">
                Kasus
              </Link>
              <span className="mx-1.5 text-gray-400">&gt;</span>
              <Link href="/manager" className="hover:underline hover:text-gray-800">
                Part Cases
              </Link>
              <span className="mx-1.5 text-gray-400">&gt;</span>
              <Link href="/technician" className="hover:underline text-gray-600 font-medium">
                Form Work Order
              </Link>
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Reload button */}
            <button
              type="button"
              onClick={() => showToast("Data meja keputusan diperbarui.")}
              title="Refresh"
              className="h-10 w-10 flex items-center justify-center rounded-xl border border-gray-300 bg-white text-gray-600 hover:text-gray-900 hover:bg-gray-50 transition-colors shadow-2xs cursor-pointer active:scale-95"
            >
              <RotateCcw className="h-4 w-4" />
            </button>

            {/* Go Back button */}
            <button
              type="button"
              onClick={() => router.push("/manager")}
              className="h-10 px-4 rounded-xl bg-[#F5C767] hover:bg-[#EEBA52] text-gray-900 font-semibold text-sm flex items-center gap-2 shadow-2xs transition-all active:scale-95 cursor-pointer"
            >
              <ArrowLeft className="h-4 w-4 stroke-[2.5]" />
              <span>GO Back</span>
            </button>
          </div>
        </div>

        {/* REKOMENDASI AGEN Yellow Banner Card */}
        <div className="rounded-2xl bg-[#F6E5B4] border border-[#ECD394] p-6 sm:p-7 shadow-xs space-y-4">
          {/* Header of Recommendation */}
          <div className="flex items-center gap-3">
            {/* AI circular badge */}
            <div className="w-6 h-6 rounded-full border-2 border-[#8C6D23] text-[#8C6D23] font-bold text-xs flex items-center justify-center shrink-0">
              AI
            </div>
            <span className="font-extrabold text-xs sm:text-sm text-[#0D5C75] tracking-wider uppercase">
              AI REKOMENDASI AGEN
            </span>
          </div>

          {/* Vendor Name & Reasoning Points */}
          <div className="space-y-1.5 pt-0.5">
            <h2 className="text-base sm:text-lg font-bold text-gray-900">
              PT Hidrolik Cepat
            </h2>
            <ul className="text-xs sm:text-sm text-gray-800 space-y-1 leading-relaxed">
              <li className="flex items-start gap-1.5">
                <span className="font-bold">•</span>
                <span>Menawarkan total biaya terendah dengan waktu pengiriman tercepat.</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="font-bold">•</span>
                <span>Memiliki riwayat kepatuhan yang baik.</span>
              </li>
              <li className="flex items-start gap-1.5">
                <span className="font-bold">•</span>
                <span>Memiliki stok yang cukup untuk memenuhi pesanan.</span>
              </li>
            </ul>
          </div>

          {/* Call to action button inside banner */}
          <div className="pt-2">
            <button
              type="button"
              onClick={() => handleSelectVendor("PT Hidrolik Cepat")}
              className="h-10 px-5 rounded-xl bg-[#0F274A] hover:bg-[#163359] text-white text-xs sm:text-sm font-semibold transition-all shadow-xs active:scale-95 cursor-pointer flex items-center gap-2"
            >
              <span>Select PT Hidrolik Cepat</span>
            </button>
          </div>
        </div>

        {/* Vendor Comparison Data Table */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs sm:text-sm border-collapse">
              {/* Table Header */}
              <thead>
                <tr className="bg-[#EAECEF] text-gray-700 font-bold uppercase text-[11px] sm:text-xs tracking-wider border-b border-gray-200">
                  <th className="py-3.5 px-4 font-bold">
                    <div className="flex items-center gap-1.5 select-none">
                      <span>VENDOR</span>
                      <ArrowUpDown className="w-3.5 h-3.5" />
                    </div>
                  </th>
                  <th className="py-3.5 px-3 font-bold">STATUS</th>
                  <th className="py-3.5 px-3 font-bold">UNIT PRICE</th>
                  <th className="py-3.5 px-3 font-bold">STOCK</th>
                  <th className="py-3.5 px-3 font-bold">DELIVERY</th>
                  <th className="py-3.5 px-3 font-bold">SHIPPING</th>
                  <th className="py-3.5 px-3 font-bold">DOWNTIME COST</th>
                  <th className="py-3.5 px-3 font-bold">TOTAL COST</th>
                  <th className="py-3.5 px-4 font-bold text-center">ACTION</th>
                </tr>
              </thead>

              {/* Table Body */}
              <tbody className="divide-y divide-gray-100 font-normal">
                {decisionRows.map((row) => {
                  return (
                    <tr
                      key={row.id}
                      className={`hover:bg-gray-50/80 transition-colors ${
                        row.isRecommended ? "bg-blue-50/20" : ""
                      }`}
                    >
                      {/* VENDOR */}
                      <td className="py-4 px-4">
                        <div className="font-semibold text-gray-900">
                          {row.vendor}
                        </div>
                        <div className="text-xs text-gray-500">
                          {row.channel}
                        </div>
                      </td>

                      {/* STATUS */}
                      <td className="py-4 px-3 font-medium text-gray-800">
                        {row.status}
                      </td>

                      {/* UNIT PRICE */}
                      <td className="py-4 px-3 font-medium text-gray-800">
                        {row.unitPrice}
                      </td>

                      {/* STOCK */}
                      <td className="py-4 px-3 text-gray-700">
                        {row.stock}
                      </td>

                      {/* DELIVERY */}
                      <td className="py-4 px-3 text-gray-700">
                        {row.delivery}
                      </td>

                      {/* SHIPPING */}
                      <td className="py-4 px-3 text-gray-700">
                        {row.shipping}
                      </td>

                      {/* DOWNTIME COST */}
                      <td className="py-4 px-3 text-gray-700">
                        {row.downtimeCost}
                      </td>

                      {/* TOTAL COST */}
                      <td className="py-4 px-3 font-semibold text-gray-900">
                        {row.totalCost}
                      </td>

                      {/* ACTION: Stacked 'Pilih Vendor' and 'Minta harga lebih baik' */}
                      <td className="py-4 px-4 text-center">
                        <div className="flex flex-col items-center justify-center gap-1.5">
                          {/* Pilih Vendor Button */}
                          <button
                            type="button"
                            onClick={() => handleSelectVendor(row.vendor)}
                            className="w-28 py-1.5 rounded-md bg-[#0F274A] hover:bg-[#152e55] text-white text-xs font-semibold shadow-2xs transition-all active:scale-95 cursor-pointer"
                          >
                            Pilih Vendor
                          </button>

                          {/* Minta harga lebih baik Button */}
                          <button
                            type="button"
                            onClick={() => handleNegotiatePrice(row.vendor)}
                            className="w-28 py-1 rounded-md border border-gray-200 bg-white hover:bg-gray-50 text-[10px] font-medium text-gray-700 shadow-2xs transition-colors cursor-pointer"
                          >
                            Minta harga lebih baik
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      {/* CONFIRMATION / ACTION MODAL */}
      {confirmationModal.show && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="relative w-full max-w-md bg-white rounded-3xl p-6 sm:p-8 shadow-2xl border border-gray-100 animate-in zoom-in-95 duration-200 space-y-4">
            <button
              type="button"
              onClick={() => setConfirmationModal({ show: false, vendor: "", type: "approve" })}
              className="absolute top-4 right-4 w-8 h-8 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors cursor-pointer"
            >
              <X className="w-5 h-5 stroke-[2]" />
            </button>

            {confirmationModal.type === "approve" ? (
              <>
                <div className="w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-700 flex items-center justify-center mx-auto">
                  <FileCheck className="w-6 h-6" />
                </div>
                <div className="text-center">
                  <h3 className="text-lg font-bold text-[#0F274A]">
                    Setujui Purchase Order?
                  </h3>
                  <p className="text-xs text-gray-500 mt-1">
                    Apakah Anda yakin ingin menyetujui Purchase Order (PO) untuk vendor {confirmationModal.vendor}?
                  </p>
                </div>
                <div className="flex items-center justify-center gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setConfirmationModal({ show: false, vendor: "", type: "approve" })}
                    className="px-4 py-2 rounded-xl border border-gray-200 text-xs font-semibold text-gray-700 hover:bg-gray-50 cursor-pointer"
                  >
                    Batal
                  </button>
                  <button
                    type="button"
                    onClick={handleConfirmApproval}
                    className="px-5 py-2 rounded-xl bg-[#0F274A] hover:bg-[#152e55] text-xs font-semibold text-white shadow-xs cursor-pointer flex items-center gap-1.5"
                  >
                    <span>Konfirmasi PO</span>
                    <Check className="w-3.5 h-3.5" />
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="w-12 h-12 rounded-2xl bg-blue-100 text-[#0F274A] flex items-center justify-center mx-auto">
                  <MessageSquare className="w-6 h-6" />
                </div>
                <div className="text-center">
                  <h3 className="text-lg font-bold text-[#0F274A]">
                    Negosiasi Harga AI
                  </h3>
                  <p className="text-xs text-gray-500 mt-1">
                    Agen AI PartPilot akan menghubungi {confirmationModal.vendor} via WhatsApp untuk meminta penawaran harga yang lebih baik.
                  </p>
                </div>
                <div className="flex items-center justify-center gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setConfirmationModal({ show: false, vendor: "", type: "approve" })}
                    className="px-4 py-2 rounded-xl border border-gray-200 text-xs font-semibold text-gray-700 hover:bg-gray-50 cursor-pointer"
                  >
                    Batal
                  </button>
                  <button
                    type="button"
                    onClick={handleConfirmNegotiation}
                    className="px-5 py-2 rounded-xl bg-[#0F274A] hover:bg-[#152e55] text-xs font-semibold text-white shadow-xs cursor-pointer flex items-center gap-1.5"
                  >
                    <span>Kirim Pesan AI</span>
                    <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
