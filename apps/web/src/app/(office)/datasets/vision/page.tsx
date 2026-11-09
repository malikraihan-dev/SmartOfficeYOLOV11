import type { Metadata } from "next";
import { VisionDatasetPage } from "@/features/datasets/vision-dataset";
export const metadata: Metadata = { title: "Dataset kamera" };
export default function Page() { return <VisionDatasetPage />; }
