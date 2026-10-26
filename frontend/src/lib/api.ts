export interface Retailer {
  id: string;
  business_name: string;
  owner_name: string | null;
  phone_number: string;
  location_name: string | null;
  accepted_crops: string[];
  is_active: boolean;
  latitude: number | null;
  longitude: number | null;
  created_at: string | null;
  leads_count: number;
}

export interface RetailerCreateInput {
  business_name: string;
  owner_name?: string;
  phone_number: string;
  location_name: string;
  latitude: number;
  longitude: number;
  accepted_crops: string[];
  is_active?: boolean;
}

export interface InquiryLog {
  id: string;
  farmer_phone: string;
  masked_farmer_phone: string;
  crop_inquired: string | null;
  location_spoken: string | null;
  matched_retailer_id: string | null;
  distance_km: number | null;
  status: 'PENDING' | 'SOLD' | 'NOT_INTERESTED' | 'NO_RESPONSE' | 'EXPIRED';
  confirmed_by: 'RETAILER' | 'FARMER' | 'SYSTEM_AUTO' | null;
  call_sid: string | null;
  timestamp: string;
}

export interface SystemStats {
  total_inquiries_today: number;
  match_rate_percentage: number;
  active_retailer_count: number;
  total_retailers: number;
}

export const DEFAULT_API_BASE_URL = 'https://ulavu-v2-backend.onrender.com';

const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_BASE_URL
).replace(/\/+$/, '');

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const fullUrl = `${API_BASE}${url}`;
  const res = await fetch(fullUrl, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {}),
    },
  });

  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export const api = {
  getStats: (): Promise<SystemStats> => fetchJson<SystemStats>('/api/stats'),

  getRetailers: (): Promise<Retailer[]> => fetchJson<Retailer[]>('/api/retailers'),

  createRetailer: (data: RetailerCreateInput): Promise<Retailer> =>
    fetchJson<Retailer>('/api/retailers', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  toggleRetailerStatus: (id: string): Promise<{ id: string; is_active: boolean; message: string }> =>
    fetchJson<{ id: string; is_active: boolean; message: string }>(`/api/retailers/${id}/toggle-status`, {
      method: 'PATCH',
    }),

  getRetailerLeads: (retailerId: string): Promise<InquiryLog[]> =>
    fetchJson<InquiryLog[]>(`/api/retailers/${retailerId}/leads`),

  updateInquiryStatus: (
    inquiryId: string,
    status: 'SOLD' | 'NOT_INTERESTED' | 'NO_RESPONSE'
  ): Promise<InquiryLog> =>
    fetchJson<InquiryLog>(`/api/inquiries/${inquiryId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),

  getAllInquiries: (): Promise<InquiryLog[]> => fetchJson<InquiryLog[]>('/api/inquiries'),
  getOptions: (): Promise<{ crops: Array<{ id: string; name: string; tamil: string }>; locations: Array<{ name: string; tamil: string; lat: number; lng: number }> }> =>
    fetchJson('/api/options'),
};
