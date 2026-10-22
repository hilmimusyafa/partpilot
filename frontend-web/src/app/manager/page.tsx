"use client"

import * as React from "react"
import Link from "next/link"
import Image from "next/image"
import { useRouter } from "next/navigation"
import {
  Search,
  SlidersHorizontal,
  Plus,
  ArrowUpDown,
  Eye,
  Pencil,
  Trash2,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Bell,
  CheckCircle2,
  X,
  Sparkles,
} from "lucide-react"

type TabType = "all" | "ai_processing" | "awaiting_you" | "escalated"

interface OrderRow {
  id: string
  vendor: string
  channel: "WhatsApp" | "Email"
  partName: string
  status: "Complete" | "Processing" | "Pending Approval" | "Escalated"
  unitPrice: number
  unitPriceFormatted: string
  stock: number
  delivery: string
  deliveryMinutesLeft: number
  shipping: number
  shippingFormatted: string
  downtimeCost: number
  downtimeCostFormatted: string
  totalCostFormatted: string
  tab: TabType
  urgency: "Low" | "Medium" | "High" | "Critical"
  aiReasoning: string
}

const initialOrders: OrderRow[] = [
  {
    id: "ORD-001",
    vendor: "PT Hidrolik Cepat",
    channel: "WhatsApp",
    partName: "Hydraulic Hose 1.5 inch High-Pressure Wire Braided",
    status: "Complete",
    unitPrice: 4200000,
    unitPriceFormatted: "Rp4,200,000",
    stock: 1,
    delivery: "Wed 16:00 (0 mins left)",
    deliveryMinutesLeft: 0,
    shipping: 150000,
    shippingFormatted: "Rp150,000",
    downtimeCost: 0,
    downtimeCostFormatted: "Rp0",
    totalCostFormatted: "Rp4.35M",
    tab: "all",
    urgency: "High",
    aiReasoning:
      "Stok ready langsung dikirim hari ini via kurir instan. Mengeliminasi downtime pabrik (penghematan Rp483.8M dibanding vendor luar kota).",
  },
  {
    id: "ORD-002",
    vendor: "PT Express Teknik",
    channel: "Email",
    partName: "Deep Groove Ball Bearing SKF 6205-2RS1 C3",
    status: "Complete",
    unitPrice: 5100000,
    unitPriceFormatted: "Rp5,100,000",
    stock: 1,
    delivery: "Wed 15:18 (0 mins left)",
    deliveryMinutesLeft: 0,
    shipping: 0,
    shippingFormatted: "Rp0",
    downtimeCost: 0,
    downtimeCostFormatted: "Rp0",
    totalCostFormatted: "Rp5.1M",
    tab: "all",
    urgency: "Medium",
    aiReasoning:
      "Pengiriman bebas ongkir dengan garansi resmi SKF Authorized. Tiba tepat waktu tanpa downtime.",
  },
  {
    id: "ORD-003",
    vendor: "CV Seal Hemat",
    channel: "WhatsApp",
    partName: "Oil Seal NBR Rotary Shaft 45x65x10mm",
    status: "Complete",
    unitPrice: 3600000,
    unitPriceFormatted: "Rp3,600,000",
    stock: 1,
    delivery: "Fri 10:00 (40h 19m left)",
    deliveryMinutesLeft: 2419,
    shipping: 100000,
    shippingFormatted: "Rp100,000",
    downtimeCost: 483800000,
    downtimeCostFormatted: "Rp483.8M",
    totalCostFormatted: "Rp487.5M",
    tab: "escalated",
    urgency: "Critical",
    aiReasoning:
      "PERINGATAN AI: Harga unit termurah (Rp3.6M), namun waktu pengiriman 40 jam menyebabkan kerugian downtime produksi sebesar Rp483.8M! Rekomendasi: Alihkan ke vendor lokal yang ready stock.",
  },
  {
    id: "ORD-004",
    vendor: "PT Hidrolik Cepat",
    channel: "WhatsApp",
    partName: "Pressure Relief Valve 250 Bar (Rexroth Compatible)",
    status: "Complete",
    unitPrice: 4200000,
    unitPriceFormatted: "Rp4,200,000",
    stock: 1,
    delivery: "Wed 16:00 (0 mins left)",
    deliveryMinutesLeft: 0,
    shipping: 150000,
    shippingFormatted: "Rp150,000",
    downtimeCost: 0,
    downtimeCostFormatted: "Rp0",
    totalCostFormatted: "Rp4.35M",
    tab: "all",
    urgency: "High",
    aiReasoning:
      "Vendor terverifikasi dengan SLA responsif via WhatsApp bot otomatis. Suku cadang sesuai standar ISO.",
  },
  {
    id: "ORD-005",
    vendor: "PT Express Teknik",
    channel: "Email",
    partName: "V-Belt Red Power 3 SPB-2000 Heavy Duty",
    status: "Complete",
    unitPrice: 5100000,
    unitPriceFormatted: "Rp5,100,000",
    stock: 1,
    delivery: "Wed 15:18 (0 mins left)",
    deliveryMinutesLeft: 0,
    shipping: 0,
    shippingFormatted: "Rp0",
    downtimeCost: 0,
    downtimeCostFormatted: "Rp0",
    totalCostFormatted: "Rp5.1M",
    tab: "all",
    urgency: "Medium",
    aiReasoning:
      "Penawaran resmi diterima melalui integrasi Email AI Parser. Bebas biaya kirim gudang Cikarang.",
  },
  {
    id: "ORD-006",
    vendor: "CV Seal Hemat",
    channel: "WhatsApp",
    partName: "Mechanical Seal Burgmann Type MG1-35",
    status: "Complete",
    unitPrice: 3600000,
    unitPriceFormatted: "Rp3,600,000",
    stock: 1,
    delivery: "Fri 10:00 (40h 19m left)",
    deliveryMinutesLeft: 2419,
    shipping: 100000,
    shippingFormatted: "Rp100,000",
    downtimeCost: 483800000,
    downtimeCostFormatted: "Rp483.8M",
    totalCostFormatted: "Rp487.5M",
    tab: "awaiting_you",
    urgency: "Critical",
    aiReasoning:
      "Dibutuhkan persetujuan manajer untuk menyetujui pengadaan alternatif lokal darurat guna mencegah downtime.",
  },
  {
    id: "ORD-007",
    vendor: "PT Hidrolik Cepat",
    channel: "WhatsApp",
    partName: "Pneumatic Cylinder DNC-63-100 Festo Spec",
    status: "Complete",
    unitPrice: 4200000,
    unitPriceFormatted: "Rp4,200,000",
    stock: 1,
    delivery: "Wed 16:00 (0 mins left)",
    deliveryMinutesLeft: 0,
    shipping: 150000,
    shippingFormatted: "Rp150,000",
    downtimeCost: 0,
    downtimeCostFormatted: "Rp0",
    totalCostFormatted: "Rp4.35M",
    tab: "all",
    urgency: "High",
    aiReasoning:
      "Telah diverifikasi sesuai spesifikasi line konveyor utama pabrik.",
  },
  {
    id: "ORD-008",
    vendor: "PT Express Teknik",
    channel: "Email",
    partName: "Temperature Sensor RTD PT100 M12 Connector",
    status: "Complete",
    unitPrice: 5100000,
    unitPriceFormatted: "Rp5,100,000",
    stock: 1,
    delivery: "Wed 15:18 (0 mins left)",
    deliveryMinutesLeft: 0,
    shipping: 0,
    shippingFormatted: "Rp0",
    downtimeCost: 0,
    downtimeCostFormatted: "Rp0",
    totalCostFormatted: "Rp5.1M",
    tab: "ai_processing",
    urgency: "Medium",
    aiReasoning:
      "AI mencocokkan kode pengganti Omron E52-THE. Validasi silang spesifikasi berhasil 100%.",
  },
  {
    id: "ORD-009",
    vendor: "PT Hidrolik Cepat",
    channel: "WhatsApp",
    partName: "Solenoid Valve 24VDC 5/2 Way 4V210-08",
    status: "Complete",
    unitPrice: 3600000,
    unitPriceFormatted: "Rp3,600,000",
    stock: 1,
    delivery: "Fri 10:00 (40h 19m left)",
    deliveryMinutesLeft: 2419,
    shipping: 100000,
    shippingFormatted: "Rp100,000",
    downtimeCost: 483800000,
    downtimeCostFormatted: "Rp483.8M",
    totalCostFormatted: "Rp487.5M",
    tab: "escalated",
    urgency: "High",
    aiReasoning:
      "Waktu pengiriman relatif lama. Memerlukan prioritas ekspres atau substitusi part cadangan gudang internal.",
  },
  {
    id: "ORD-010",
    vendor: "CV Seal Hemat",
    channel: "WhatsApp",
    partName: "Coupling Element Rotex GR-28 92 Shore A",
    status: "Complete",
    unitPrice: 4200000,
    unitPriceFormatted: "Rp4,200,000",
    stock: 1,
    delivery: "Wed 16:00 (0 mins left)",
    deliveryMinutesLeft: 0,
    shipping: 150000,
    shippingFormatted: "Rp150,000",
    downtimeCost: 0,
    downtimeCostFormatted: "Rp0",
    totalCostFormatted: "Rp4.35M",
    tab: "all",
    urgency: "Low",
    aiReasoning:
      "Tersedia untuk maintenance preventif terjadwal. Bebas risiko downtime.",
  },
]

export default function ManagerOrderListPage() {
  const router = useRouter()

  // Filter & Search states
  const [activeTab, setActiveTab] = React.useState<TabType>("all")
  const [searchQuery, setSearchQuery] = React.useState("")
  const [urgencyFilter, setUrgencyFilter] = React.useState<string>("All")
  const [showUrgencyDropdown, setShowUrgencyDropdown] = React.useState(false)

  // Orders list
  const [orders, setOrders] = React.useState<OrderRow[]>(initialOrders)
  const searchInputRef = React.useRef<HTMLInputElement>(null)

  // Load dynamically submitted orders from localStorage (submitted by Technician flow)
  React.useEffect(() => {
    try {
      const stored = localStorage.getItem("partpilot_orders")
      if (stored) {
        const parsed: OrderRow[] = JSON.parse(stored)
        if (Array.isArray(parsed) && parsed.length > 0) {
          // Merge custom orders on top of existing mock data
          setOrders([...parsed, ...initialOrders])
        }
      }
    } catch {}
  }, [])

  // Keyboard shortcut listener for ⌘ K
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault()
        searchInputRef.current?.focus()
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [])

  // Detail Modal state
  const [selectedOrder, setSelectedOrder] = React.useState<OrderRow | null>(null)

  // Pagination state
  const [currentPage, setCurrentPage] = React.useState(1)

  // Toast state
  const [toastMessage, setToastMessage] = React.useState<string | null>(null)

  const showToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(null), 3000)
  }

  // Filtered orders
  const filteredOrders = React.useMemo(() => {
    return orders.filter((order) => {
      // Tab filter
      if (activeTab === "ai_processing" && order.tab !== "ai_processing") return false
      if (activeTab === "awaiting_you" && order.tab !== "awaiting_you") return false
      if (activeTab === "escalated" && order.tab !== "escalated") return false

      // Urgency filter
      if (urgencyFilter !== "All" && order.urgency !== urgencyFilter) return false

      // Search query
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase()
        const matchVendor = order.vendor.toLowerCase().includes(query)
        const matchChannel = order.channel.toLowerCase().includes(query)
        const matchPart = order.partName.toLowerCase().includes(query)
        const matchStatus = order.status.toLowerCase().includes(query)
        if (!matchVendor && !matchChannel && !matchPart && !matchStatus) return false
      }

      return true
    })
  }, [orders, activeTab, urgencyFilter, searchQuery])

  // Delete row handler
  const handleDeleteRow = (id: string, vendor: string) => {
    setOrders((prev) => prev.filter((o) => o.id !== id))
    showToast(`Order from ${vendor} archived.`)
  }

  // Quick edit note/status
  const handleEditRow = (order: OrderRow) => {
    showToast(`Editing order ${order.id} (${order.vendor})`)
    setSelectedOrder(order)
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
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
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
            {/* Order List Link (Active) */}
            <span className="text-sm font-bold text-[#0F274A] cursor-pointer">
              Order List
            </span>

            {/* Notification Bell */}
            <button
              type="button"
              onClick={() =>
                showToast("2 high downtime risk alerts require manager attention!")
              }
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
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-5">
        {/* Title Header & Search Bar Row */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-[#0F274A]">
              ORDER LIST
            </h1>
            <p className="text-xs sm:text-sm text-gray-500 mt-0.5">
              <Link href="/" className="hover:underline hover:text-gray-800">
                Home
              </Link>
              <span className="mx-1.5 text-gray-400">&gt;</span>
              <span className="text-gray-600 font-medium">
                Order List
              </span>
            </p>
          </div>

          {/* Search Bar with ⌘ K shortcut badge */}
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search order..."
              className="w-full h-10 pl-9 pr-14 rounded-xl border border-gray-300 bg-white text-xs sm:text-sm text-gray-800 placeholder:text-gray-400 focus:outline-hidden focus:border-[#0F274A] focus:ring-1 focus:ring-[#0F274A] transition-all shadow-2xs"
            />
            <div className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none">
              <kbd className="px-1.5 py-0.5 text-[10px] font-semibold text-gray-400 bg-gray-100 border border-gray-200 rounded">
                ⌘ K
              </kbd>
            </div>
          </div>
        </div>

        {/* Filters Tabs & Action Buttons Row */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          {/* Left: Tab Pills */}
          <div className="flex flex-wrap items-center gap-2.5">
            {/* All (24) */}
            <button
              type="button"
              onClick={() => setActiveTab("all")}
              className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
                activeTab === "all"
                  ? "bg-[#0F274A] text-white shadow-xs"
                  : "bg-white border border-[#0F274A] text-[#0F274A] hover:bg-gray-50"
              }`}
            >
              All (24)
            </button>

            {/* AI Processing */}
            <button
              type="button"
              onClick={() => setActiveTab("ai_processing")}
              className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
                activeTab === "ai_processing"
                  ? "bg-[#0F274A] text-white shadow-xs"
                  : "bg-white border border-[#0F274A] text-[#0F274A] hover:bg-gray-50"
              }`}
            >
              AI Processing (3)
            </button>

            {/* Awaiting You */}
            <button
              type="button"
              onClick={() => setActiveTab("awaiting_you")}
              className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
                activeTab === "awaiting_you"
                  ? "bg-[#0F274A] text-white shadow-xs"
                  : "bg-white border border-[#0F274A] text-[#0F274A] hover:bg-gray-50"
              }`}
            >
              Awaiting You (1)
            </button>

            {/* Escalated */}
            <button
              type="button"
              onClick={() => setActiveTab("escalated")}
              className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
                activeTab === "escalated"
                  ? "bg-[#0F274A] text-white shadow-xs"
                  : "bg-white border border-[#0F274A] text-[#0F274A] hover:bg-gray-50"
              }`}
            >
              Escalated (1)
            </button>
          </div>

          {/* Right: Filter Urgency & Create Work Order */}
          <div className="flex items-center gap-3 relative">
            {/* Filter Urgency Dropdown Button */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setShowUrgencyDropdown(!showUrgencyDropdown)}
                className="h-10 px-3.5 rounded-xl border border-gray-300 bg-white hover:bg-gray-50 text-gray-700 text-xs sm:text-sm font-semibold flex items-center gap-2 shadow-2xs transition-colors cursor-pointer"
              >
                <SlidersHorizontal className="w-4 h-4 text-gray-500" />
                <span>
                  {urgencyFilter === "All"
                    ? "Filter Urgency"
                    : `Urgency: ${urgencyFilter}`}
                </span>
              </button>

              {/* Urgency Dropdown Menu */}
              {showUrgencyDropdown && (
                <div className="absolute right-0 mt-2 w-40 bg-white rounded-xl shadow-lg border border-gray-200 py-1.5 z-30 animate-in fade-in zoom-in-95">
                  {["All", "Critical", "High", "Medium", "Low"].map((level) => {
                    const label = level === "All" ? "All Urgency" : level
                    return (
                      <button
                        key={level}
                        type="button"
                        onClick={() => {
                          setUrgencyFilter(level)
                          setShowUrgencyDropdown(false)
                        }}
                        className={`w-full text-left px-3.5 py-1.5 text-xs font-medium hover:bg-gray-50 transition-colors cursor-pointer flex items-center justify-between ${
                          urgencyFilter === level
                            ? "text-[#0F274A] font-bold bg-blue-50/50"
                            : "text-gray-700"
                        }`}
                      >
                        <span>{label}</span>
                        {urgencyFilter === level && (
                          <span className="w-1.5 h-1.5 rounded-full bg-[#0F274A]" />
                        )}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>

            {/* + Create Work Order Button */}
            <button
              type="button"
              onClick={() => router.push("/technician")}
              className="h-10 px-4 rounded-xl bg-[#0F274A] hover:bg-[#152e55] text-white text-xs sm:text-sm font-semibold flex items-center gap-2 shadow-2xs transition-all active:scale-95 cursor-pointer"
            >
              <Plus className="w-4 h-4 stroke-[2.5]" />
              <span>Create Work Order</span>
            </button>
          </div>
        </div>

        {/* Main Data Table Container */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs sm:text-sm border-collapse">
              {/* Table Header */}
              <thead>
                <tr className="bg-[#EAECEF] text-gray-700 font-bold uppercase text-[11px] sm:text-xs tracking-wider border-b border-gray-200">
                  <th className="py-3.5 px-4 font-bold">
                    <div className="flex items-center gap-1.5 cursor-pointer hover:text-gray-900 select-none">
                      <span>VENDOR</span>
                      <ArrowUpDown className="w-3.5 h-3.5" />
                    </div>
                  </th>
                  <th className="py-3.5 px-3 font-bold">STATUS</th>
                  <th className="py-3.5 px-3 font-bold">UNIT PRICE</th>
                  <th className="py-3.5 px-3 font-bold">STOCK</th>
                  <th className="py-3.5 px-3 font-bold">DELIVERY</th>
                  <th className="py-3.5 px-3 font-bold">SHIPPING</th>
                  <th className="py-3.5 px-3 font-bold leading-tight">
                    <div>DOWNTIME COST</div>
                  </th>
                  <th className="py-3.5 px-3 font-bold">TOTAL COST</th>
                  <th className="py-3.5 px-4 font-bold text-center">ACTION</th>
                </tr>
              </thead>

              {/* Table Body */}
              <tbody className="divide-y divide-gray-100 font-normal">
                {filteredOrders.length === 0 ? (
                  <tr>
                    <td
                      colSpan={9}
                      className="py-12 text-center text-sm text-gray-400"
                    >
                      No orders matching the criteria.
                    </td>
                  </tr>
                ) : (
                  filteredOrders.map((row) => {
                    const isHighDowntime = row.downtimeCost > 0
                    return (
                      <tr
                        key={row.id}
                        className={`hover:bg-gray-50/80 transition-colors ${
                          isHighDowntime ? "bg-amber-50/20" : ""
                        }`}
                      >
                        {/* Vendor & Channel */}
                        <td className="py-3.5 px-4">
                          <Link
                            href="/manager/decision"
                            className="font-semibold text-gray-900 hover:text-blue-600 hover:underline block"
                          >
                            {row.vendor}
                          </Link>
                          <div className="text-xs text-gray-500">
                            ({row.channel})
                          </div>
                        </td>

                        {/* Status */}
                        <td className="py-3.5 px-3 font-medium text-gray-800">
                          {row.status}
                        </td>

                        {/* Unit Price */}
                        <td className="py-3.5 px-3 font-medium text-gray-800">
                          {row.unitPriceFormatted}
                        </td>

                        {/* Stock */}
                        <td className="py-3.5 px-3 text-gray-700">
                          {row.stock}
                        </td>

                        {/* Delivery */}
                        <td className="py-3.5 px-3 text-gray-700 whitespace-nowrap">
                          {row.delivery}
                        </td>

                        {/* Shipping */}
                        <td className="py-3.5 px-3 text-gray-700">
                          {row.shippingFormatted}
                        </td>

                        {/* Downtime Cost */}
                        <td className="py-3.5 px-3">
                          {isHighDowntime ? (
                            <span className="font-bold text-amber-700 bg-amber-100/70 px-2 py-0.5 rounded-md inline-block">
                              {row.downtimeCostFormatted}
                            </span>
                          ) : (
                            <span className="text-gray-700">
                              {row.downtimeCostFormatted}
                            </span>
                          )}
                        </td>

                        {/* Total Cost */}
                        <td className="py-3.5 px-3 font-semibold text-gray-900">
                          {row.totalCostFormatted}
                        </td>

                        {/* Action Icons: Eye (View), Pencil (Edit), Trash (Delete) */}
                        <td className="py-3.5 px-4">
                          <div className="flex items-center justify-center gap-1.5">
                            {/* View Details Button -> Navigate to Meja Keputusan */}
                            <button
                              type="button"
                              onClick={() => router.push("/manager/decision")}
                              title="View Order Details & AI Reason"
                              className="w-7 h-7 rounded-lg border border-gray-200 bg-white hover:bg-blue-50 hover:text-blue-600 hover:border-blue-300 flex items-center justify-center text-gray-600 transition-colors cursor-pointer shadow-2xs"
                            >
                              <Eye className="w-3.5 h-3.5" />
                            </button>

                            {/* Edit Button */}
                            <button
                              type="button"
                              onClick={() => handleEditRow(row)}
                              title="Edit / Update Note"
                              className="w-7 h-7 rounded-lg border border-gray-200 bg-white hover:bg-gray-100 flex items-center justify-center text-gray-600 transition-colors cursor-pointer shadow-2xs"
                            >
                              <Pencil className="w-3.5 h-3.5" />
                            </button>

                            {/* Trash Button */}
                            <button
                              type="button"
                              onClick={() => handleDeleteRow(row.id, row.vendor)}
                              title="Archive / Remove"
                              className="w-7 h-7 rounded-lg border border-gray-200 bg-white hover:bg-red-50 hover:text-red-600 hover:border-red-300 flex items-center justify-center text-gray-600 transition-colors cursor-pointer shadow-2xs"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Centered Pagination matching Screenshot: «  ‹  1  2  3  4  ...  ›  » */}
          <div className="py-4 border-t border-gray-100 flex items-center justify-center gap-2 select-none">
            {/* First « */}
            <button
              type="button"
              onClick={() => setCurrentPage(1)}
              className="p-1.5 text-gray-500 hover:text-gray-900 transition-colors cursor-pointer"
            >
              <ChevronsLeft className="w-4 h-4 stroke-[2]" />
            </button>

            {/* Prev ‹ */}
            <button
              type="button"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              className="p-1.5 text-gray-500 hover:text-gray-900 transition-colors cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4 stroke-[2]" />
            </button>

            {/* Number 1 (Active) */}
            <button
              type="button"
              onClick={() => setCurrentPage(1)}
              className={`w-7 h-7 rounded-full text-xs font-semibold flex items-center justify-center transition-all cursor-pointer ${
                currentPage === 1
                  ? "bg-[#0F274A] text-white shadow-xs"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
            >
              1
            </button>

            {/* Number 2 */}
            <button
              type="button"
              onClick={() => setCurrentPage(2)}
              className={`w-7 h-7 rounded-full text-xs font-semibold flex items-center justify-center transition-all cursor-pointer ${
                currentPage === 2
                  ? "bg-[#0F274A] text-white shadow-xs"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
            >
              2
            </button>

            {/* Number 3 */}
            <button
              type="button"
              onClick={() => setCurrentPage(3)}
              className={`w-7 h-7 rounded-full text-xs font-semibold flex items-center justify-center transition-all cursor-pointer ${
                currentPage === 3
                  ? "bg-[#0F274A] text-white shadow-xs"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
            >
              3
            </button>

            {/* Number 4 */}
            <button
              type="button"
              onClick={() => setCurrentPage(4)}
              className={`w-7 h-7 rounded-full text-xs font-semibold flex items-center justify-center transition-all cursor-pointer ${
                currentPage === 4
                  ? "bg-[#0F274A] text-white shadow-xs"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
            >
              4
            </button>

            {/* Ellipsis ... */}
            <span className="text-gray-400 text-xs px-1 font-semibold">...</span>

            {/* Next › */}
            <button
              type="button"
              onClick={() => setCurrentPage((p) => Math.min(4, p + 1))}
              className="p-1.5 text-gray-500 hover:text-gray-900 transition-colors cursor-pointer"
            >
              <ChevronRight className="w-4 h-4 stroke-[2]" />
            </button>

            {/* Last » */}
            <button
              type="button"
              onClick={() => setCurrentPage(4)}
              className="p-1.5 text-gray-500 hover:text-gray-900 transition-colors cursor-pointer"
            >
              <ChevronsRight className="w-4 h-4 stroke-[2]" />
            </button>
          </div>
        </div>
      </main>

      {/* DETAIL MODAL: AI Decision Breakdown & PO Approval */}
      {selectedOrder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="relative w-full max-w-xl bg-white rounded-3xl p-6 sm:p-8 shadow-2xl border border-gray-100 animate-in zoom-in-95 duration-200 space-y-5">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-gray-100 pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-[#0F274A]">
                    {selectedOrder.id}
                  </span>
                  <span className="text-xs text-gray-500 font-medium">
                    Channel: {selectedOrder.channel}
                  </span>
                </div>
                <h3 className="text-lg font-bold text-[#0F274A] mt-1">
                  {selectedOrder.vendor}
                </h3>
                <p className="text-xs text-gray-600 mt-0.5">
                  Part:{" "}
                  <span className="font-semibold text-gray-900">
                    {selectedOrder.partName}
                  </span>
                </p>
              </div>

              <button
                type="button"
                onClick={() => setSelectedOrder(null)}
                className="w-8 h-8 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors cursor-pointer"
              >
                <X className="w-5 h-5 stroke-[2]" />
              </button>
            </div>

            {/* AI Reasoning Insight Box */}
            <div className="rounded-2xl p-4 bg-blue-50/70 border border-blue-200/80 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-[#0F274A]">
                <Sparkles className="w-4 h-4 text-amber-500 shrink-0" />
                <span>PartPilot AI Decision Explanation</span>
              </div>
              <p className="text-xs text-gray-700 leading-relaxed">
                {selectedOrder.aiReasoning}
              </p>
            </div>

            {/* Cost Breakdown Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-gray-50 rounded-2xl p-4 border border-gray-200 text-xs">
              <div>
                <span className="text-gray-500 block">Unit Price:</span>
                <span className="font-bold text-gray-800">
                  {selectedOrder.unitPriceFormatted}
                </span>
              </div>
              <div>
                <span className="text-gray-500 block">Delivery:</span>
                <span className="font-semibold text-gray-800">
                  {selectedOrder.delivery}
                </span>
              </div>
              <div>
                <span className="text-gray-500 block">Downtime Risk:</span>
                <span
                  className={`font-bold ${
                    selectedOrder.downtimeCost > 0
                      ? "text-red-600"
                      : "text-emerald-600"
                  }`}
                >
                  {selectedOrder.downtimeCostFormatted}
                </span>
              </div>
              <div>
                <span className="text-gray-500 block">Total Economic Cost:</span>
                <span className="font-bold text-[#0F274A] text-sm">
                  {selectedOrder.totalCostFormatted}
                </span>
              </div>
            </div>

            {/* Action Buttons in Modal */}
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setSelectedOrder(null)}
                className="px-4 py-2.5 rounded-xl border border-gray-200 text-xs font-semibold text-gray-700 hover:bg-gray-50 transition-colors cursor-pointer"
              >
                Close
              </button>
              <button
                type="button"
                onClick={() => {
                  showToast(`Purchase Order to ${selectedOrder.vendor} Approved!`)
                  setSelectedOrder(null)
                }}
                className="px-5 py-2.5 rounded-xl bg-[#0F274A] hover:bg-[#152e55] text-xs font-semibold text-white shadow-xs transition-all active:scale-95 cursor-pointer flex items-center gap-1.5"
              >
                <span>Approve Purchase Order</span>
                <CheckCircle2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
