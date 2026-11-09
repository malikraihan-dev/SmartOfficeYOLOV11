export type Zone = { x1: number; y1: number; x2: number; y2: number };
export type AdminSession = { authenticated: boolean; configured: boolean; user?: { username: string; role: "admin" }; csrf_token?: string };
export type Snapshot = { url: string; person_count: number; confidence_percent: number; captured_at: string; trigger: string };
export type OfficeStatus = {
  person_count: number; person_confidence: number; visual_activity: string;
  desk_objects: string[];
  co2_ppm: number | null; temperature_c: number | null; humidity_percent: number | null;
  sensor_status: string; sensor_updated_at: string | null; final_validation: string;
  snapshots: Snapshot[]; camera_status: string; last_frame_at: string | null;
  camera_fps: number; inference_ms: number; frame_brightness: number | null; dark_frame: boolean;
  dark_frame_events: number; audio_available: boolean; audio_status: string; audio_label: string;
  audio_level_dbfs: number | null; audio_threshold_dbfs: number; audio_calibration_progress: number;
  detection_confidence_threshold: number; zone_config: Zone; model_name: string;
  zone_duration_sec: number; zone_entries_today: number; zone_exits_today: number;
};
export type SensorRow = {
  id: number; timestamp: string; co2_ppm: number; temperature_c: number;
  humidity_percent: number; source: "scd40";
};
export type SensorDataset = {
  total_rows: number; first_at: string | null; last_at: string | null; source: "scd40";
  rows: SensorRow[]; forecast_status: "not_connected"; horizon_minutes: number; note: string;
};
export type VisionSample = {
  id: number; captured_at: string; predicted_count: number; confidence: number;
  activity: string; image_url: string; actual_count: number | null;
};
export type VisionEvaluation = {
  reviewed_samples: number; exact_count_matches: number; count_accuracy_percent: number | null;
  pending_count: number; samples: VisionSample[]; metric_note: string;
};
export type AudioEvaluation = {
  available: boolean; accuracy_percent: number | null; reviewed_samples: number;
  class_metrics: Record<string, { precision_percent: number; recall_percent: number; f1_percent: number; support: number }>;
  samples: { id: number; sampled_at: string; level_dbfs: number; predicted_label: string; actual_label: string | null }[];
};
