import type { Metadata } from "next";
import { Monitoring } from "@/features/monitoring/monitoring";
export const metadata: Metadata = { title: "Monitoring" };
export default function Page() { return <Monitoring />; }
