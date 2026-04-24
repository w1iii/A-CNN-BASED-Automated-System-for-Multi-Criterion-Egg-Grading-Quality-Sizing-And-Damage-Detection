import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, Token } from '../types';
import { apiClient } from '../api/client';

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  
  login: (email: string, password: string) => Promise<boolean>;
  register: (email: string, username: string, password: string) => Promise<boolean>;
  logout: () => void;
  checkAuth: () => Promise<boolean>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isLoading: false,
      error: null,

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          const data: Token = await apiClient.login(email, password);
          localStorage.setItem('token', data.access_token);
          set({ token: data.access_token, isLoading: false });
          return await get().checkAuth();
        } catch (error: unknown) {
          const message = error instanceof Error ? error.message : 'Login failed';
          set({ error: message, isLoading: false });
          return false;
        }
      },

      register: async (email: string, username: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          await apiClient.register(email, username, password);
          return await get().login(email, password);
        } catch (error: unknown) {
          const message = error instanceof Error ? error.message : 'Registration failed';
          set({ error: message, isLoading: false });
          return false;
        }
      },

      logout: () => {
        localStorage.removeItem('token');
        set({ user: null, token: null, error: null });
      },

      checkAuth: async () => {
        const token = localStorage.getItem('token');
        if (!token) {
          set({ token: null, user: null });
          return false;
        }
        set({ token });
        try {
          const user = await apiClient.getMe();
          set({ user });
          return true;
        } catch {
          localStorage.removeItem('token');
          set({ token: null, user: null });
          return false;
        }
      },
    }),
    { name: 'auth-storage', partialize: (state) => ({ token: state.token }) }
  )
);