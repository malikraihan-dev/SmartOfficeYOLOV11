import type { Metadata } from "next";
import { ModelsPage } from "@/features/models/models";
export const metadata: Metadata = { title: "Model" };
export default function Page() { return <ModelsPage />; }
