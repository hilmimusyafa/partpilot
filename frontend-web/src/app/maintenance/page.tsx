"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
export default function MaintenanceRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace("/"); }, [router]);
  return <p className="p-8">Membuka PartPilot… <Link href="/">Buka beranda</Link></p>;
}
