import axios from 'axios';

// When deployed on Vercel or in production, VITE_API_URL can be set to an external backend,
// or defaults to empty string which routes to relative '/api' (handled by Vercel Serverless Functions)
export const API_BASE_URL = import.meta.env.VITE_API_URL !== undefined
  ? import.meta.env.VITE_API_URL
  : (import.meta.env.DEV ? 'http://localhost:8000' : '');

export const api = axios.create({
  baseURL: API_BASE_URL,
});

export const getApiUrl = (endpoint: string): string => {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${API_BASE_URL}${cleanEndpoint}`;
};

export default api;
