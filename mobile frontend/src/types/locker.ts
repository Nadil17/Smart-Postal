export interface Locker {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  address: string;
  small_available: number;
  medium_available: number;
  large_available: number;
  total_slots: number;
  operating_hours: string;
  is_active: boolean;
}

export interface LockerRecommendation {
  id: string;
  name: string;
  address?: string;
  latitude: number;
  longitude: number;
  score: number;
  distance: string;
  availability: {
    small: number;
    medium: number;
    large: number;
  };
  route_deviation: string;
  predicted_availability: number;
}

export interface RecommendationRequest {
  latitude: number;
  longitude: number;
  courier_route: [number, number][];
  package_size?: 'small' | 'medium' | 'large';
}

export interface RecommendationResponse {
  success: boolean;
  recommendations: LockerRecommendation[];
  processing_time_ms: number;
}