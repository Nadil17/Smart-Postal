import { createContext, useContext, useState, type ReactNode } from 'react';

export interface DeliveryOrder {
    id: string;
    recipientName: string;
    address: string;
    status: 'pending' | 'delivered' | 'locker';
    neighborNicImage?: string; // URL of uploaded NIC
    neighborName?: string;
    voiceEnrolled?: boolean;
    lat?: number;
    lng?: number;
}

export interface User {
    id: string;
    username: string;
    email: string;
    fullName: string;
    phone?: string;
    password: string;
    role: 'client' | 'courier' | 'admin';
    verified: boolean;
    joinDate: string;
    status: 'active' | 'inactive' | 'suspended';
}

interface RegisterData {
    username: string;
    email: string;
    password: string;
    fullName: string;
    phone?: string;
    role: 'client' | 'courier';
}

interface DatabaseContextType {
    orders: DeliveryOrder[];
    updateOrder: (id: string, updates: Partial<DeliveryOrder>) => void;
    currentUserRole: 'client' | 'courier' | 'admin' | null;
    setRole: (role: 'client' | 'courier' | 'admin' | null) => void;
    isAuthenticated: boolean;
    currentUser: string | null;
    users: User[];
    login: (username: string, password: string) => boolean;
    register: (data: RegisterData) => { success: boolean; error?: string };
    logout: () => void;
}

const DatabaseContext = createContext<DatabaseContextType | undefined>(undefined);

export const DatabaseProvider = ({ children }: { children: ReactNode }) => {
    const [currentUserRole, setRole] = useState<'client' | 'courier' | 'admin' | null>(null);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [currentUser, setCurrentUser] = useState<string | null>(null);

    // Mock users database
    const [users, setUsers] = useState<User[]>([
        {
            id: 'U001',
            username: 'client',
            email: 'client@smartpostal.com',
            fullName: 'Demo Client',
            password: 'client123',
            role: 'client',
            verified: true,
            joinDate: '2024-01-01',
            status: 'active'
        },
        {
            id: 'U002',
            username: 'courier',
            email: 'courier@smartpostal.com',
            fullName: 'Demo Courier',
            password: 'courier123',
            role: 'courier',
            verified: true,
            joinDate: '2024-01-01',
            status: 'active'
        },
        {
            id: 'U003',
            username: 'admin',
            email: 'admin@smartpostal.com',
            fullName: 'Admin User',
            password: 'admin123',
            role: 'admin',
            verified: true,
            joinDate: '2024-01-01',
            status: 'active'
        }
    ]);

    // Mock initial data
    const [orders, setOrders] = useState<DeliveryOrder[]>([
        {
            id: 'ORD-001',
            recipientName: 'Kamal Perera',
            address: '123, Galle Road, Colombo 03',
            status: 'pending',
            voiceEnrolled: false,
            lat: 6.9271,
            lng: 79.8612
        },
        {
            id: 'ORD-002',
            recipientName: 'Nimali Silva',
            address: '45/B, Kandy Road, Kelaniya',
            status: 'pending',
            voiceEnrolled: true,
            lat: 6.9147,
            lng: 79.8778
        },
        {
            id: 'ORD-003',
            recipientName: 'Sunil Perera',
            address: '10, Duplication Road, Colombo 04',
            status: 'pending',
            voiceEnrolled: false,
            lat: 6.8969,
            lng: 79.8587
        }
    ]);

    const updateOrder = (id: string, updates: Partial<DeliveryOrder>) => {
        setOrders(prev => prev.map(order =>
            order.id === id ? { ...order, ...updates } : order
        ));
    };

    const login = (username: string, password: string): boolean => {
        const user = users.find(u => u.username === username && u.password === password);
        
        if (user && user.status === 'active') {
            setIsAuthenticated(true);
            setCurrentUser(user.username);
            setRole(user.role);
            return true;
        }
        return false;
    };

    const register = (data: RegisterData): { success: boolean; error?: string } => {
        // Check if username already exists
        if (users.find(u => u.username === data.username)) {
            return { success: false, error: 'Username already taken' };
        }

        // Check if email already exists
        if (users.find(u => u.email === data.email)) {
            return { success: false, error: 'Email already registered' };
        }

        // Create new user
        const newUser: User = {
            id: `U${String(users.length + 1).padStart(3, '0')}`,
            username: data.username,
            email: data.email,
            fullName: data.fullName,
            phone: data.phone,
            password: data.password,
            role: data.role,
            verified: false,
            joinDate: new Date().toISOString().split('T')[0],
            status: 'active'
        };

        setUsers([...users, newUser]);
        return { success: true };
    };

    const logout = () => {
        setIsAuthenticated(false);
        setCurrentUser(null);
        setRole(null);
    };

    return (
        <DatabaseContext.Provider value={{ orders, updateOrder, currentUserRole, setRole, isAuthenticated, currentUser, users, login, register, logout }}>
            {children}
        </DatabaseContext.Provider>
    );
};

export const useDatabase = () => {
    const context = useContext(DatabaseContext);
    if (!context) {
        throw new Error('useDatabase must be used within a DatabaseProvider');
    }
    return context;
};
