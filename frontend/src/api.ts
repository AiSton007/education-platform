import axios, { AxiosInstance } from "axios";

const baseURL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:18080";

export const api: AxiosInstance = axios.create({ baseURL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error?.response?.status === 401) localStorage.removeItem("access_token");
    return Promise.reject(error);
  },
);

export type Role = "employee" | "manager" | "admin";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  access_expires_in: number;
  refresh_expires_in: number;
}

export interface Me {
  id: string;
  email: string;
  role: Role;
}

export interface TestSummary {
  id: string;
  title: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Option {
  id: string;
  order: number;
  text: string;
  is_correct?: boolean;
}

export interface Question {
  id: string;
  order: number;
  type: "single" | "multiple" | "free_text";
  text: string;
  weight: number;
  options: Option[];
}

export interface Test extends TestSummary {
  questions: Question[];
}

export interface Attempt {
  id: string;
  test_id: string;
  user_id: string;
  status: string;
  score: number | null;
  report_id: string | null;
  analysis_id: string | null;
  error: string | null;
  started_at: string;
  submitted_at: string | null;
  completed_at: string | null;
}

export interface Report {
  id: string;
  attempt_id: string;
  user_id: string;
  analysis_id: string;
  score: number;
  data: {
    strengths: string[];
    weaknesses: string[];
    score: number;
    recommendations: Array<{ topic: string; resource_url?: string; reason: string }>;
  };
  created_at: string;
  recommendations: Array<{ id: string; topic: string; resource_url: string | null; reason: string }>;
}

export const login = (email: string, password: string) =>
  api.post<TokenPair>("/api/v1/auth/login", { email, password }).then((r) => r.data);

export const register = (payload: {
  email: string;
  password: string;
  full_name: string;
  department?: string;
  position?: string;
  role?: Role;
}) => api.post("/api/v1/auth/register", payload).then((r) => r.data);

export const fetchMe = () => api.get<Me>("/api/v1/auth/me").then((r) => r.data);
export const listTests = () =>
  api.get<{ items: TestSummary[]; total: number }>("/api/v1/tests").then((r) => r.data);
export const getTest = (id: string) => api.get<Test>(`/api/v1/tests/${id}`).then((r) => r.data);
export const startAttempt = (testId: string) =>
  api.post<Attempt>(`/api/v1/tests/${testId}/start`).then((r) => r.data);
export const postAnswers = (
  attemptId: string,
  answers: Array<{ question_id: string; selected_option_ids?: string[]; free_text?: string }>,
) => api.post<Attempt>(`/api/v1/attempts/${attemptId}/answers`, { answers }).then((r) => r.data);
export const submitAttempt = (attemptId: string) =>
  api.post<{ attempt_id: string; report_id: string | null; status: string }>(
    `/api/v1/attempts/${attemptId}/submit`,
  ).then((r) => r.data);
export const getReport = (id: string) => api.get<Report>(`/api/v1/reports/${id}`).then((r) => r.data);
