import type { Metadata } from "next";
import { SensorDatasetPage } from "@/features/sensors/sensor-dataset";
export const metadata: Metadata = { title: "Dataset sensor" };
export default function Page() { return <SensorDatasetPage />; }
