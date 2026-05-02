export interface User {
  id: number;
  email: string;
  username: string;
  created_at: string;
  is_active: boolean;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface DetectionBox {
  id: number;
  class_name: string;
  confidence: number;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  annotated: boolean;
  size_category?: 'small' | 'medium' | 'large';
  weight_g?: number;
  grade?: 'AA' | 'A' | 'B' | 'N/A' | 'Reject';
}

export interface Prediction {
  id: number;
  file_name: string;
  file_type: string;
  file_path: string;
  status: string;
  total_detections: number;
  damaged_count: number;
  not_damaged_count: number;
  processing_time_ms: number | null;
  created_at: string;
  completed_at: string | null;
}

export interface PredictionDetail extends Prediction {
  result_json: Record<string, unknown> | null;
  annotated_path: string | null;
  detection_boxes: DetectionBox[];
}

export interface DashboardStats {
  total_predictions: number;
  total_images: number;
  total_videos: number;
  total_detections: number;
  damaged_percentage: number;
  avg_processing_time_ms: number;
  recent_predictions: Prediction[];
  grade_distribution?: GradeDistribution;
}

export interface HealthStatus {
  status: string;
  model_loaded: boolean;
  database_connected: boolean;
}

export interface GradeDistribution {
  grade_aa: number;
  grade_a: number;
  grade_b: number;
  grade_na: number;
  grade_reject: number;
  total: number;
}

export interface UserSettings {
  mm_per_pixel: number;
}