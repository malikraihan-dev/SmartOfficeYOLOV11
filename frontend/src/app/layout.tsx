import type { Metadata } from "next";
import "@/styles/tokens.css";
import "./globals.css";
import "@/styles/console.css";
import "@/styles/saas.css";

export const metadata: Metadata = { title: { default: "Smart Office", template: "%s | Smart Office" }, description: "Pemantauan ruang kerja, kamera YOLOv11, dan dataset sensor SCD40." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="id"><body>{children}</body></html>;
}
