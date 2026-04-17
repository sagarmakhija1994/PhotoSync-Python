import axios from 'axios';

const getToken = () => localStorage.getItem('jwt_token');

// 💥 THE FAIL-PROOF ROUTING 💥
// In production (.exe), baseURL is just an empty string ''.
// This forces Axios to natively append requests to whatever IP:Port is in the URL bar!
const baseURL = import.meta.env.MODE === 'development' ? 'http://127.0.0.1:8000' : '';

export const api = axios.create({
  baseURL: baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor
api.interceptors.request.use(
  (config) => {
    const token = getToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('jwt_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);