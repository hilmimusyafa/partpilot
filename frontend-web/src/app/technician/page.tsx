"use client"

import * as React from "react"
import Link from "next/link"
import Image from "next/image"
import { useRouter } from "next/navigation"
import {
  RotateCcw,
  ArrowLeft,
  ChevronDown,
  Minus,
  Plus,
  Search,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Loader2,
  ArrowRight,
} from "lucide-react"

type UrgencyLevel = "Low" | "Medium" | "High" | "Critical"

interface PartPilotDraft {
  description: string
  machine: string
  quantity: number
  urgency: UrgencyLevel
  notes: string
  savedAt: string
}

export default function TechnicianWorkOrderPage() {
  const router = useRouter()

  // Form states
  const [description, setDescription] = React.useState("")
  const [machine, setMachine] = React.useState("")
  const [quantity, setQuantity] = React.useState(0)
  const [urgency, setUrgency] = React.useState<UrgencyLevel>("Low")
  const [notes, setNotes] = React.useState("")

  // UI feedback & processing states
  const [toast, setToast] = React.useState<{
    show: boolean
    type: "success" | "info" | "warning"
    message: string
  }>({ show: false, type: "info", message: "" })

  const [isSearching, setIsSearching] = React.useState(false)
  const [searchStep, setSearchStep] = React.useState("")

  // Load draft from localStorage on mount if present
  React.useEffect(() => {
    try {
      const saved = localStorage.getItem("partpilot_technician_draft")
      if (saved) {
        const parsed: PartPilotDraft = JSON.parse(saved)
        if (parsed.description) setDescription(parsed.description)
        if (parsed.machine) setMachine(parsed.machine)
        if (typeof parsed.quantity === "number") setQuantity(parsed.quantity)
        if (parsed.urgency) setUrgency(parsed.urgency)
        if (parsed.notes) setNotes(parsed.notes)
      }
    } catch {
      // ignore parsing errors
    }
  }, [])

  const triggerToast = (
    message: string,
    type: "success" | "info" | "warning" = "info"
  ) => {
    setToast({ show: true, type, message })
    setTimeout(() => {
      setToast((prev) => ({ ...prev, show: false }))
    }, 3500)
  }

  // Handle Quantity adjustments
  const handleDecrement = () => {
    setQuantity((prev) => (prev > 0 ? prev - 1 : 0))
  }

  const handleIncrement = () => {
    setQuantity((prev) => prev + 1)
  }

  // Reset form
  const handleReset = () => {
    setDescription("")
    setMachine("")
    setQuantity(0)
    setUrgency("Low")
    setNotes("")
    try {
      localStorage.removeItem("partpilot_technician_draft")
    } catch {}
    triggerToast("Form has been reset.", "info")
  }

  // Save Draft to localStorage
  const handleSaveDraft = () => {
    try {
      const draftData: PartPilotDraft = {
        description,
        machine,
        quantity,
        urgency,
        notes,
        savedAt: new Date().toISOString(),
      }
      localStorage.setItem(
        "partpilot_technician_draft",
        JSON.stringify(draftData)
      )
      triggerToast("Draft saved successfully!", "success")
    } catch {
      triggerToast("Failed to save draft.", "warning")
    }
  }

  // Find Parts action with AI analysis simulation & navigation to Clarification
  const handleFindParts = () => {
    const effectiveDesc = description.trim() || "Motor drive bearing worn out and noisy"
    const effectiveMachine = machine || "Conveyor Line 1"
    const effectiveQty = quantity > 0 ? quantity : 1

    setDescription(effectiveDesc)
    if (!machine) setMachine(effectiveMachine)
    if (quantity <= 0) setQuantity(effectiveQty)

    // Save to draft
    try {
      const draftData: PartPilotDraft = {
        description: effectiveDesc,
        machine: effectiveMachine,
        quantity: effectiveQty,
        urgency,
        notes,
        savedAt: new Date().toISOString(),
      }
      localStorage.setItem("partpilot_technician_draft", JSON.stringify(draftData))
    } catch {}

    setIsSearching(true)
    setSearchStep("Analyzing reported problem & machinery context...")

    setTimeout(() => {
      setSearchStep("Mapping OEM parts and warehouse availability...")
    }, 700)

    setTimeout(() => {
      setIsSearching(false)
      router.push("/technician/clarification")
    }, 1400)
  }

  // Machine options
  const machineList = [
    "Mixer 2 (Line Produksi A)",
    "Conveyor Line 1",
    "Pompa Kimia NBR-45",
    "Boiler B-01",
    "Crusher Mill 3",
    "Extruder Unit 4",
    "Packaging Machine 02",
    "Hydraulic Press HP-100",
  ]

  // Urgency options
  const urgencyList: UrgencyLevel[] = ["Low", "Medium", "High", "Critical"]

  return (
    <div className="min-h-screen bg-[#F1F3F6] text-gray-800 flex flex-col font-sans">
      {/* Toast Notification */}
      {toast.show && (
        <div className="fixed top-5 right-5 z-50 flex items-center gap-2.5 px-4 py-3 rounded-xl shadow-lg border text-sm font-medium transition-all duration-200 bg-white border-gray-200 text-gray-800 animate-in fade-in slide-in-from-top-3">
          {toast.type === "success" && (
            <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
          )}
          {toast.type === "warning" && (
            <AlertCircle className="h-5 w-5 text-amber-500 shrink-0" />
          )}
          {toast.type === "info" && (
            <Sparkles className="h-5 w-5 text-blue-600 shrink-0" />
          )}
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
              <Link href="/" className="hover:underline hover:text-gray-800">
                Home
              </Link>
              <span className="mx-1.5 text-gray-400">&gt;</span>
              <span className="text-gray-600">
                Form Work Order
              </span>
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

            {/* Go Back Button -> Back to Landing Page */}
            <button
              type="button"
              onClick={() => router.push("/")}
              className="h-10 px-4 rounded-xl bg-[#F5C767] hover:bg-[#EEBA52] text-gray-900 font-semibold text-sm flex items-center gap-2 shadow-2xs transition-all active:scale-95 cursor-pointer"
            >
              <ArrowLeft className="h-4 w-4 stroke-[2.5]" />
              <span>GO Back</span>
            </button>
          </div>
        </div>

        {/* Form Card */}
        <div className="bg-white rounded-2xl border border-gray-200/90 shadow-xs p-6 sm:p-8 space-y-6">
          {/* Card Header: Icon + Title + Subtitle */}
          <div className="flex items-start gap-3">
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

          {/* Problem Description Textarea */}
          <div className="relative">
            <textarea
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Can you describe the problem? (e.g. noise, leak, broken part)"
              className="w-full rounded-xl border border-gray-200 bg-[#FBFBFC] sm:bg-white p-4 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-hidden focus:border-[#0F274A] focus:ring-1 focus:ring-[#0F274A] transition-all resize-y min-h-[120px]"
            />
          </div>

          {/* Row: Machine & Quantity */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 sm:gap-6">
            {/* Machine Selection Dropdown */}
            <div>
              <label className="block text-xs sm:text-sm font-semibold text-gray-800 mb-2">
                Machine <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <select
                  value={machine}
                  onChange={(e) => setMachine(e.target.value)}
                  className="h-11 w-full appearance-none rounded-xl border border-gray-200 bg-white px-4 pr-10 text-sm text-gray-800 focus:border-[#0F274A] focus:outline-hidden focus:ring-1 focus:ring-[#0F274A] transition-all cursor-pointer"
                >
                  <option value="" disabled>
                    Select Machine
                  </option>
                  {machineList.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
              </div>
            </div>

            {/* Quantity Stepper */}
            <div>
              <label className="block text-xs sm:text-sm font-semibold text-gray-800 mb-2">
                Quantity <span className="text-red-500">*</span>
              </label>
              <div className="flex items-center gap-2">
                {/* Decrement Button */}
                <button
                  type="button"
                  onClick={handleDecrement}
                  aria-label="Decrease quantity"
                  className="h-11 w-11 shrink-0 rounded-xl border border-gray-200 bg-white hover:bg-gray-50 active:bg-gray-100 flex items-center justify-center text-gray-700 transition-colors cursor-pointer select-none"
                >
                  <Minus className="h-4 w-4 stroke-[2.5]" />
                </button>

                {/* Number Display Box */}
                <div className="flex-1 h-11 rounded-xl border border-gray-200 bg-white flex items-center justify-center">
                  <input
                    type="number"
                    min={0}
                    value={quantity}
                    onChange={(e) => {
                      const val = parseInt(e.target.value, 10)
                      setQuantity(isNaN(val) || val < 0 ? 0 : val)
                    }}
                    className="w-full text-center text-sm font-semibold text-gray-800 bg-transparent border-none outline-hidden focus:ring-0"
                  />
                </div>

                {/* Increment Button */}
                <button
                  type="button"
                  onClick={handleIncrement}
                  aria-label="Increase quantity"
                  className="h-11 w-11 shrink-0 rounded-xl border border-gray-200 bg-white hover:bg-gray-50 active:bg-gray-100 flex items-center justify-center text-gray-700 transition-colors cursor-pointer select-none"
                >
                  <Plus className="h-4 w-4 stroke-[2.5]" />
                </button>
              </div>
            </div>
          </div>

          {/* Row: Urgency */}
          <div>
            <label className="block text-xs sm:text-sm font-semibold text-gray-800 mb-2">
              Urgency <span className="text-red-500">*</span>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
              {urgencyList.map((level) => {
                const isSelected = urgency === level
                return (
                  <button
                    key={level}
                    type="button"
                    onClick={() => setUrgency(level)}
                    className={`h-11 rounded-xl border text-sm font-medium transition-all cursor-pointer flex items-center justify-center ${
                      isSelected
                        ? "border-[#0F274A] bg-[#0F274A] text-white shadow-xs"
                        : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50"
                    }`}
                  >
                    {level}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Row: Additional Notes */}
          <div>
            <label className="block text-xs sm:text-sm font-semibold text-gray-800 mb-2">
              Notes
            </label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Any additional information..."
              className="h-11 w-full rounded-xl border border-gray-200 bg-white px-4 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-hidden focus:border-[#0F274A] focus:ring-1 focus:ring-[#0F274A] transition-all"
            />
          </div>

          {/* Bottom Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-2">
            {/* Find Parts Button */}
            <button
              type="button"
              disabled={isSearching}
              onClick={handleFindParts}
              className="h-11 px-5 rounded-xl bg-[#F5C767] hover:bg-[#EEBA52] text-gray-900 font-semibold text-sm flex items-center gap-2 shadow-2xs transition-all active:scale-95 cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <span>Find Parts</span>
              <Search className="h-4 w-4 stroke-[2.2]" />
            </button>

            {/* Save Draft Button */}
            <button
              type="button"
              onClick={handleSaveDraft}
              className="h-11 px-5 rounded-xl bg-[#1A2F50] hover:bg-[#13233D] text-white font-semibold text-sm flex items-center gap-2 shadow-2xs transition-all active:scale-95 cursor-pointer"
            >
              <span>Save Draft</span>
              <svg
                className="w-4 h-4 text-white"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <path d="M12 18v-6" />
                <path d="M9 15l3 3 3-3" />
              </svg>
            </button>
          </div>
        </div>
      </main>

      {/* AI Processing Modal */}
      {isSearching && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 sm:p-8 shadow-2xl border border-gray-100 text-center space-y-4 animate-in fade-in zoom-in-95">
            <div className="w-14 h-14 rounded-2xl bg-amber-50 text-[#F5C767] flex items-center justify-center mx-auto border border-amber-200">
              <Loader2 className="w-7 h-7 animate-spin text-amber-500" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-[#0F274A]">
                PartPilot AI Reasoning
              </h3>
              <p className="text-xs text-gray-500 mt-1">
                Multi-Agent System is working...
              </p>
            </div>
            <div className="bg-gray-50 rounded-xl p-3.5 border border-gray-200 text-xs text-gray-700 font-mono text-left">
              <div className="flex items-center gap-2">
                <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                <span>{searchStep}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
