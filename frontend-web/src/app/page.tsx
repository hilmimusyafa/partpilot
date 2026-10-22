"use client"

import * as React from "react"
import Link from "next/link"
import Image from "next/image"
import { ChevronDown } from "lucide-react"

export default function LandingPage() {
  const detailsRef = React.useRef<HTMLDetailsElement>(null)

  // Auto close details dropdown when clicking outside
  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        detailsRef.current &&
        detailsRef.current.open &&
        !detailsRef.current.contains(event.target as Node)
      ) {
        detailsRef.current.open = false
      }
    }
    document.addEventListener("click", handleClickOutside)
    return () => {
      document.removeEventListener("click", handleClickOutside)
    }
  }, [])

  return (
    <div className="min-h-screen bg-[#F0F2F5] flex items-center justify-center p-4 font-sans select-none relative">
      {/* Outer Card container matching screenshot frame */}
      <div className="w-full max-w-4xl min-h-[560px] bg-[#F7F9FC] rounded-3xl border border-gray-200/80 shadow-xs flex flex-col items-center justify-center p-8 sm:p-12 relative overflow-hidden">
        {/* Subtle decorative background glow */}
        <div className="absolute inset-0 bg-radial from-white via-transparent to-transparent opacity-70 pointer-events-none" />

        {/* Center Content */}
        <div className="relative z-10 flex flex-col items-center text-center">
          {/* Logo */}
          <div className="mb-2 flex items-center justify-center">
            <Image
              src="/logo.png"
              alt="PartPilot Logo"
              width={180}
              height={64}
              priority
              className="h-10 sm:h-12 w-auto object-contain drop-shadow-2xs"
            />
          </div>

          {/* Title */}
          <h1 className="mt-3 text-xl sm:text-2xl font-bold tracking-tight text-[#0F274A]">
            Welcome to PartPilot
          </h1>

          {/* Subtitle */}
          <p className="mt-1.5 text-xs sm:text-sm text-gray-500 font-normal">
            Pilih peran untuk membuka PartPilot
          </p>

          {/* Native HTML <details> Dropdown: Works 100% natively in every browser */}
          <div className="mt-6 flex flex-col items-center z-30">
            <details
              ref={detailsRef}
              className="group relative flex flex-col items-center"
            >
              {/* Login Button matching screenshot gradient pill */}
              <summary
                className="w-48 h-10 px-5 flex items-center justify-center gap-2 bg-gradient-to-r from-[#17375E] via-[#245480] to-[#519BBF] text-white text-xs sm:text-sm font-semibold shadow-md hover:shadow-lg transition-all active:scale-95 cursor-pointer rounded-full group-open:rounded-b-none group-open:rounded-t-2xl list-none [&::-webkit-details-marker]:hidden select-none outline-hidden"
              >
                <span>Pilih peran</span>
                <ChevronDown className="w-3.5 h-3.5 transition-transform duration-200 stroke-[2.5] group-open:rotate-180" />
              </summary>

              {/* Dropdown Menu (matching '00 - Landing Page (select)') */}
              <div className="w-48 bg-gradient-to-b from-[#2E6080]/90 via-[#C4DCE8] to-[#E2EDF3] rounded-b-2xl shadow-xl border border-t-0 border-[#2E6080]/30 overflow-hidden flex flex-col">
                {/* Manager Option */}
                <Link
                  href="/manager"
                  className="w-full text-left px-5 py-3 text-xs sm:text-sm font-semibold text-[#0F274A] hover:bg-white/60 transition-colors cursor-pointer border-b border-[#2E6080]/15 flex items-center justify-between group/link"
                >
                  <span className="group-hover/link:translate-x-0.5 transition-transform">
                    Manager
                  </span>
                  <span className="text-[10px] text-gray-600 font-normal opacity-70">
                    /manager
                  </span>
                </Link>

                {/* Technician Option */}
                <Link
                  href="/technician"
                  className="w-full text-left px-5 py-3 text-xs sm:text-sm font-semibold text-[#0F274A] hover:bg-white/60 transition-colors cursor-pointer flex items-center justify-between group/link"
                >
                  <span className="group-hover/link:translate-x-0.5 transition-transform">
                    Technician
                  </span>
                  <span className="text-[10px] text-gray-600 font-normal opacity-70">
                    /technician
                  </span>
                </Link>
              </div>
            </details>
          </div>

          {/* Quick Direct Access Buttons as immediate backup */}
          <div className="mt-8 pt-4 border-t border-gray-200/60 flex items-center gap-3">
            <span className="text-[11px] text-gray-400 font-medium">
              Quick link:
            </span>
            <Link
              href="/technician"
              className="text-xs font-semibold text-[#17375E] hover:underline px-2.5 py-1 rounded-md bg-blue-50/80 hover:bg-blue-100 transition-colors cursor-pointer"
            >
              🔧 Technician
            </Link>
            <span className="text-gray-300 text-xs">|</span>
            <Link
              href="/manager"
              className="text-xs font-semibold text-[#17375E] hover:underline px-2.5 py-1 rounded-md bg-blue-50/80 hover:bg-blue-100 transition-colors cursor-pointer"
            >
              👔 Manager
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
