"use client"

import * as React from "react"
import Link from "next/link"
import Image from "next/image"
import { useRouter, useSearchParams } from "next/navigation"
import {
  RotateCcw,
  ArrowLeft,
  X,
  Sparkles,
  ArrowRight,
} from "lucide-react"

function ClarificationContent() {
  const router = useRouter()
  const searchParams = useSearchParams()

  // Form states
  const [clarificationAnswer, setClarificationAnswer] = React.useState("")

  // Modal popup state (Teknisi - 03 Data Berhasil Masuk)
  const isAutoOpen = searchParams?.get("submitted") === "true" || searchParams?.get("popup") === "true"
  const [showSuccessModal, setShowSuccessModal] = React.useState<boolean>(isAutoOpen)

  // Toast feedback state
  const [toast, setToast] = React.useState<{
    show: boolean
    message: string
  }>({ show: false, message: "" })

  const triggerToast = (message: string) => {
    setToast({ show: true, message })
    setTimeout(() => {
      setToast({ show: false, message: "" })
    }, 3000)
  }

  // Quick specification presets for easy testing
  const quickSpecs = [
    "Diameter poros 25 mm (Tipe 6205)",
    "Diameter luar 52 mm, tebal 15 mm",
    "Diameter selang 1.5 inch (High Pressure)",
    "Seal NBR Diameter 45 mm",
  ]

  const handleReset = () => {
    setClarificationAnswer("")
    triggerToast("Clarification field reset.")
  }

  // Submit action: directly opens the requested popup (Teknisi - 03 Data Berhasil Masuk)
  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    
    // Save new work order to localStorage so it seamlessly appears in Manager Order List
    try {
      const existing = JSON.parse(localStorage.getItem("partpilot_orders") || "[]")
      const draft = JSON.parse(localStorage.getItem("partpilot_technician_draft") || "{}")
      const newId = `ORD-0${existing.length + 11}`
      const newOrder = {
        id: newId,
        vendor: "PT Hidrolik Cepat",
        channel: "WhatsApp",
        partName: clarificationAnswer || draft.description || "High-Pressure Hydraulic Part (Verified)",
        status: "Complete",
        unitPrice: 4200000,
        unitPriceFormatted: "Rp4,200,000",
        stock: draft.quantity || 1,
        delivery: "Wed 16:00 (0 mins left)",
        deliveryMinutesLeft: 0,
        shipping: 150000,
        shippingFormatted: "Rp150,000",
        downtimeCost: 0,
        downtimeCostFormatted: "Rp0",
        totalCostFormatted: "Rp4.35M",
        tab: "all",
        urgency: draft.urgency || "High",
        aiReasoning: "Order baru diajukan teknisi. AI PartPilot mencocokkan spesifikasi OEM dan merekomendasikan PT Hidrolik Cepat karena ready stock.",
      }
      localStorage.setItem("partpilot_orders", JSON.stringify([newOrder, ...existing]))
    } catch {}

    // Open the success popup modal immediately as requested in screenshot 03
    setShowSuccessModal(true)
  }

  const handleGoBack = () => {
    setShowSuccessModal(false)
    router.push("/technician")
  }

  return (
    <div className="min-h-screen bg-[#F1F3F6] text-gray-800 flex flex-col font-sans relative">
      {/* Toast Notification */}
      {toast.show && (
        <div className="fixed top-5 right-5 z-60 flex items-center gap-2.5 px-4 py-3 rounded-xl shadow-lg border text-sm font-medium transition-all bg-white border-gray-200 text-gray-800 animate-in fade-in slide-in-from-top-3">
          <Sparkles className="h-5 w-5 text-blue-600 shrink-0" />
          <span>{toast.message}</span>
        </div>
      )}

      {/* Top Navbar */}
      <header className="w-full bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          {/* Left: LOGO */}
          <div className="flex items-center gap-6">
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

          {/* Right: User Profile Avatar */}
          <div className="flex items-center gap-4">
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

      {/* Main Content Area */}
      <main className="flex-1 w-full max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-5">
        {/* Title Header & Actions Row */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-[#0F274A]">
              FORM WORK ORDER
            </h1>
            <p className="text-xs sm:text-sm text-gray-500 mt-0.5">
              <Link
                href="/"
                className="hover:underline hover:text-gray-700"
              >
                Home
              </Link>
              <span className="mx-1.5 text-gray-400">&gt;</span>
              <Link
                href="/manager"
                className="hover:underline text-gray-500"
              >
                Cases
              </Link>
              <span className="mx-1.5 text-gray-400">&gt;</span>
              <Link
                href="/technician"
                className="hover:underline text-gray-600 font-medium"
              >
                Form Work Order
              </Link>
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Refresh / Reset Button */}
            <button
              type="button"
              onClick={handleReset}
              title="Reset Form"
              className="h-10 w-10 flex items-center justify-center rounded-xl border border-gray-300 bg-white text-gray-600 hover:text-gray-900 hover:bg-gray-50 transition-colors shadow-2xs cursor-pointer active:scale-95"
            >
              <RotateCcw className="h-4 w-4" />
            </button>

            {/* Go Back Button */}
            <button
              type="button"
              onClick={() => router.push("/technician")}
              className="h-10 px-4 rounded-xl bg-[#F5C767] hover:bg-[#EEBA52] text-gray-900 font-semibold text-sm flex items-center gap-2 shadow-2xs transition-all active:scale-95 cursor-pointer"
            >
              <ArrowLeft className="h-4 w-4 stroke-[2.5]" />
              <span>GO Back</span>
            </button>
          </div>
        </div>

        {/* Form Card (Teknisi - 02 Klarifikasi AI View) */}
        <div className="bg-white rounded-2xl border border-gray-200/90 shadow-xs p-6 sm:p-8 space-y-6">
          {/* Centered AI Question Banner */}
          <div className="flex justify-center pt-1 pb-2">
            <div className="inline-flex items-center gap-3 px-5 py-3 rounded-2xl bg-[#F8E8B6] border border-[#F3D58C] shadow-2xs text-[#1F2937]">
              {/* AI circle badge */}
              <div className="w-6 h-6 rounded-full border-2 border-[#8C6D23] text-[#8C6D23] font-bold text-xs flex items-center justify-center shrink-0">
                AI
              </div>
              <span className="font-semibold text-xs sm:text-sm text-[#1F2937] leading-snug">
                Coba ukur, berapa diameter part yang dibutuhkan?
              </span>
            </div>
          </div>

          {/* Problem Description & Required Parts Header */}
          <div className="flex items-start gap-3 pt-1">
            <div className="mt-0.5 text-[#0F274A] shrink-0">
              <svg
                className="w-6 h-6 text-[#0F274A]"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 3l1.5 3.5L17 8l-3.5 1.5L12 13l-1.5-3.5L7 8l3.5-1.5L12 3z" />
                <path d="M18 13l.8 1.8 1.8.8-1.8.8-.8 1.8-.8-1.8-1.8-.8 1.8-.8.8-1.8z" />
                <path d="M4 18l.8 1.8 1.8.8-1.8.8-.8 1.8-.8-1.8-1.8-.8 1.8-.8.8-1.8z" />
              </svg>
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-bold text-[#0F274A]">
                Problem Description & Required Parts
              </h2>
              <p className="text-xs sm:text-sm text-gray-500 mt-0.5">
                Tell us what happened and what parts you think you need
              </p>
            </div>
          </div>

          {/* Textarea */}
          <div className="relative">
            <textarea
              rows={4}
              value={clarificationAnswer}
              onChange={(e) => setClarificationAnswer(e.target.value)}
              placeholder="Can you describe the problem? (e.g. noise, leak, broken part)"
              className="w-full rounded-xl border border-gray-200 bg-[#FBFBFC] sm:bg-white p-4 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-hidden focus:border-[#0F274A] focus:ring-1 focus:ring-[#0F274A] transition-all resize-y min-h-[140px]"
            />
          </div>

          {/* Quick preset chips to help technician test easily */}
          <div className="space-y-2 pt-1">
            <span className="text-xs font-semibold text-gray-500">
              Saran Cepat:
            </span>
            <div className="flex flex-wrap gap-2">
              {quickSpecs.map((spec) => (
                <button
                  key={spec}
                  type="button"
                  onClick={() => setClarificationAnswer(spec)}
                  className="px-3 py-1.5 rounded-lg border border-gray-200 bg-gray-50 hover:bg-gray-100 text-xs font-medium text-gray-700 transition-colors cursor-pointer"
                >
                  + {spec}
                </button>
              ))}
            </div>
          </div>

          {/* Action Row */}
          <div className="flex items-center justify-between pt-4 border-t border-gray-100">
            <Link
              href="/technician"
              className="inline-flex items-center gap-1.5 text-xs sm:text-sm font-semibold text-gray-500 hover:text-gray-800 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Form Work Order</span>
            </Link>

            <button
              type="button"
              onClick={() => handleSubmit()}
              className="h-11 px-6 rounded-xl bg-[#F5C767] hover:bg-[#EEBA52] text-gray-900 font-semibold text-sm flex items-center gap-2 shadow-2xs transition-all active:scale-95 cursor-pointer"
            >
              <span>Submit Report</span>
              <ArrowRight className="h-4 w-4 stroke-[2.5]" />
            </button>
          </div>
        </div>
      </main>

      {/* POPUP MODAL: Teknisi - 03 Data Berhasil Masuk */}
      {showSuccessModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs transition-opacity animate-in fade-in duration-200">
          <div className="relative w-full max-w-lg bg-white rounded-3xl p-8 sm:p-12 shadow-2xl border border-gray-100 text-center animate-in zoom-in-95 duration-200">
            {/* Close 'X' Button at Top Right */}
            <button
              type="button"
              onClick={() => setShowSuccessModal(false)}
              aria-label="Close modal"
              className="absolute top-5 right-5 w-8 h-8 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors cursor-pointer"
            >
              <X className="w-5 h-5 stroke-[2]" />
            </button>

            {/* Real Logo Image */}
            <div className="pt-2 flex justify-center">
              <Image
                src="/logo.png"
                alt="PartPilot Logo"
                width={140}
                height={50}
                className="h-9 w-auto object-contain"
              />
            </div>

            {/* Thank You for the Report! Title */}
            <h2 className="mt-6 text-xl sm:text-2xl font-bold tracking-tight text-[#0F274A]">
              Thank You for the Report!
            </h2>

            {/* Description Subtitle */}
            <p className="mt-3 text-xs sm:text-sm text-gray-500 leading-relaxed max-w-sm mx-auto font-normal">
              We&apos;ve received your submission. We will inform the manager to review the problem and the needed parts.
            </p>

            {/* Custom Pill Gradient 'GO Back' Button & Manager Shortcut */}
            <div className="mt-8 flex flex-col items-center gap-3">
              <button
                type="button"
                onClick={handleGoBack}
                className="inline-flex items-center justify-center gap-2.5 px-8 py-3 rounded-full bg-gradient-to-r from-[#17375E] via-[#245480] to-[#519BBF] hover:opacity-95 text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all active:scale-95 cursor-pointer select-none"
              >
                <svg
                  className="w-4 h-4 text-white"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="19" y1="12" x2="5" y2="12" />
                  <polyline points="12 19 5 12 12 5" />
                </svg>
                <span className="tracking-wide">GO Back</span>
              </button>

              <button
                type="button"
                onClick={() => router.push("/manager")}
                className="text-xs text-gray-500 hover:text-[#0F274A] hover:underline font-medium transition-colors cursor-pointer"
              >
                View in Manager Order List &rarr;
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function TechnicianClarificationPage() {
  return (
    <React.Suspense fallback={<div className="min-h-screen bg-[#F1F3F6]" />}>
      <ClarificationContent />
    </React.Suspense>
  )
}
