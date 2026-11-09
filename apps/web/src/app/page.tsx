import type { Metadata } from "next";
import { LandingPage } from "@/features/landing/landing-page";
export const metadata: Metadata = { title: "Analitik ruang kerja", description: "Kenali aktivitas dan kondisi ruang kerja melalui Smart Office: monitoring visual, sensor SCD40, dan riwayat data dalam satu dashboard." };
export default function Home() { return <LandingPage />; }
