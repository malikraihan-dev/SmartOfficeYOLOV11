import type { Metadata } from "next";
import { Suspense } from "react";
import { LoginForm } from "@/features/auth/login-form";
export const metadata: Metadata = { title: "Masuk admin" };
export default function LoginPage() { return <Suspense fallback={<div className="loading-state">Menyiapkan halaman masuk…</div>}><LoginForm /></Suspense>; }
