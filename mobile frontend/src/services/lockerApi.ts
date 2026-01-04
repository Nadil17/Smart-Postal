import type { 
  Locker, 
  RecommendationRequest, 
  RecommendationResponse 
} from '../types/locker';

const API_BASE_URL = 'http://127.0.0.1:8000';
const LOCKER_BASE = `${API_BASE_URL}/api/lockers`;

// Get auth token from localStorage
const getAuthHeaders = (): HeadersInit => {
  const token = localStorage.getItem('token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
};

export const lockerApi = {
  /**
   * Get AI-powered locker recommendations
   * Uses ST-GNN model for prediction
   */
  getRecommendations: async (request: RecommendationRequest): Promise<RecommendationResponse> => {
    const response = await fetch(`${LOCKER_BASE}/recommend`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(request)
    });
    return response.json();
  },

  /**
   * Get all available lockers
   */
  getAllLockers: async (): Promise<Locker[]> => {
    const response = await fetch(`${LOCKER_BASE}/`, {
      headers: getAuthHeaders()
    });
    return response.json();
  },

  /**
   * Get locker by ID
   */
  getLockerById: async (lockerId: string): Promise<Locker> => {
    const response = await fetch(`${LOCKER_BASE}/${lockerId}`, {
      headers: getAuthHeaders()
    });
    return response.json();
  },

  /**
   * Reserve a locker slot for an order
   */
  reserveSlot: async (lockerId: string, orderId: number, slotSize: string): Promise<any> => {
    const response = await fetch(`${LOCKER_BASE}/${lockerId}/reserve`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ order_id: orderId, slot_size: slotSize })
    });
    return response.json();
  },

  /**
   * Get locker availability status
   */
  getAvailability: async (lockerId: string): Promise<any> => {
    const response = await fetch(`${LOCKER_BASE}/${lockerId}/availability`, {
      headers: getAuthHeaders()
    });
    return response.json();
  },

  /**
   * Unlock locker with verification code
   */
  unlockLocker: async (lockerId: string, verificationCode: string): Promise<any> => {
    const response = await fetch(`${LOCKER_BASE}/${lockerId}/unlock`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ verification_code: verificationCode })
    });
    return response.json();
  }
};

export default lockerApi;