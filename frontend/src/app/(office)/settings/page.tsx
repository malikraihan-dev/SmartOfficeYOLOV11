import type { Metadata } from "next";
import { SettingsPage } from "@/features/settings/settings";
export const metadata: Metadata = { title: "Pengaturan" };
export default function Page() { return <SettingsPage />; }
