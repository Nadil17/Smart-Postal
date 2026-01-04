// API Service for Smart Postal Backend
const API_BASE_URL = 'http://127.0.0.1:8000';

// Get auth token from localStorage
const getAuthToken = (): string | null => {
    return localStorage.getItem('token');
};

// Create headers with auth
const getAuthHeaders = (): HeadersInit => {
    const token = getAuthToken();
    return {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };
};

// Order types matching backend schema
export interface BackendOrder {
    id: number;
    order_number: string;
    customer_id: number;
    courier_id: number | null;
    delivery_address: string;
    delivery_city: string;
    delivery_postal_code: string;
    delivery_instructions: string | null;
    status: 'pending' | 'biometric_enrolled' | 'in_transit' | 'out_for_delivery' | 'delivered' | 'cancelled' | 'failed';
    total_amount: number;
    voice_enrolled: boolean;
    fingerprint_enrolled: boolean;
    verification_required: boolean;
    created_at: string;
    updated_at: string | null;
    delivered_at: string | null;
}

// Frontend order format (for compatibility with existing components)
export interface FrontendOrder {
    id: string;
    orderId: number;
    orderNumber: string;
    recipientName: string;
    address: string;
    city: string;
    status: 'pending' | 'delivered' | 'locker' | 'in_transit' | 'out_for_delivery';
    customerId: number;
    courierId: number | null;
    voiceEnrolled: boolean;
    verificationRequired: boolean;
    totalAmount: number;
    neighborNicImage?: string;
    neighborName?: string;
}

// Convert backend order to frontend format
export const mapBackendToFrontend = (order: BackendOrder): FrontendOrder => {
    // Map backend status to frontend status
    let frontendStatus: FrontendOrder['status'] = 'pending';
    switch (order.status) {
        case 'pending':
        case 'biometric_enrolled':
            frontendStatus = 'pending';
            break;
        case 'in_transit':
            frontendStatus = 'in_transit';
            break;
        case 'out_for_delivery':
            frontendStatus = 'out_for_delivery';
            break;
        case 'delivered':
            frontendStatus = 'delivered';
            break;
        case 'cancelled':
        case 'failed':
            frontendStatus = 'locker'; // Treat failed as locker redirect
            break;
    }

    return {
        id: order.order_number, // Use order_number as display ID
        orderId: order.id,      // Keep numeric ID for API calls
        orderNumber: order.order_number,
        recipientName: `Customer #${order.customer_id}`, // Will be replaced with actual name
        address: order.delivery_address,
        city: order.delivery_city,
        status: frontendStatus,
        customerId: order.customer_id,
        courierId: order.courier_id,
        voiceEnrolled: order.voice_enrolled,
        verificationRequired: order.verification_required,
        totalAmount: order.total_amount,
    };
};

// API Functions
export const ordersApi = {
    // Get all orders for current user (based on role)
    async getOrders(): Promise<FrontendOrder[]> {
        const response = await fetch(`${API_BASE_URL}/api/orders/`, {
            method: 'GET',
            headers: getAuthHeaders()
        });

        if (response.status === 401) {
            // Token expired - clear storage and redirect to login
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = '/login';
            throw new Error('Session expired. Please login again.');
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Failed to fetch orders' }));
            throw new Error(error.detail || 'Failed to fetch orders');
        }

        const backendOrders: BackendOrder[] = await response.json();
        return backendOrders.map(mapBackendToFrontend);
    },

    // Get single order by ID
    async getOrder(orderId: number): Promise<FrontendOrder> {
        const response = await fetch(`${API_BASE_URL}/api/orders/${orderId}`, {
            method: 'GET',
            headers: getAuthHeaders()
        });

        if (response.status === 401) {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = '/login';
            throw new Error('Session expired. Please login again.');
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Order not found' }));
            throw new Error(error.detail || 'Order not found');
        }

        const backendOrder: BackendOrder = await response.json();
        return mapBackendToFrontend(backendOrder);
    },

    // Update order status
    async updateOrderStatus(orderId: number, status: string): Promise<FrontendOrder> {
        const response = await fetch(`${API_BASE_URL}/api/orders/${orderId}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({ status })
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Failed to update order' }));
            throw new Error(error.detail || 'Failed to update order');
        }

        const backendOrder: BackendOrder = await response.json();
        return mapBackendToFrontend(backendOrder);
    },

    // Create new order (for customers)
    async createOrder(orderData: {
        delivery_address: string;
        delivery_city: string;
        delivery_postal_code: string;
        delivery_instructions?: string;
        total_amount: number;
        verification_required?: boolean;
    }): Promise<FrontendOrder> {
        const response = await fetch(`${API_BASE_URL}/api/orders/`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(orderData)
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Failed to create order' }));
            throw new Error(error.detail || 'Failed to create order');
        }

        const backendOrder: BackendOrder = await response.json();
        return mapBackendToFrontend(backendOrder);
    }
};

// User API
export const usersApi = {
    // Get user by ID
    async getUser(userId: number): Promise<{ id: number; full_name: string; email: string }> {
        const response = await fetch(`${API_BASE_URL}/api/users/${userId}`, {
            method: 'GET',
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error('User not found');
        }

        return await response.json();
    }
};

export default { ordersApi, usersApi };
