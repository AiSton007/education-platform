import axios, { AxiosInstance } from "axios";
import { jwtDecode } from "jwt-decode";

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
    if (error?.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    }
    return Promise.reject(error);
  },
);

export type Role = "employee" | "manager" | "admin";

interface JwtPayload {
  sub: string;
  role: Role;
  email?: string;
  exp: number;
}

export function getStoredRole(): Role | null {
  const token = localStorage.getItem("access_token");
  if (!token) return null;
  try {
    const payload = jwtDecode<JwtPayload>(token);
    if (payload.exp && payload.exp * 1000 < Date.now()) return null;
    return payload.role;
  } catch {
    return null;
  }
}

export function getStoredUserId(): string | null {
  const token = localStorage.getItem("access_token");
  if (!token) return null;
  try {
    return jwtDecode<JwtPayload>(token).sub;
  } catch {
    return null;
  }
}

export function isAuthenticated(): boolean {
  return getStoredRole() !== null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  access_expires_in: number;
  refresh_expires_in: number;
}

export interface Me {
  user_id: string;
  email: string;
  full_name: string;
  department: string | null;
  position: string | null;
  role: Role;
  is_active: boolean;
}

export interface TestSummary {
  id: string;
  title: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  questions_count: number;
}

export interface Question {
  id: string;
  order: number;
  type: "single" | "multiple" | "free_text";
  text: string;
  weight: number;
}

export interface QuestionAdmin extends Question {
  correct_answer: string;
}

export interface Test extends TestSummary {
  questions: Question[];
}

export interface TestAdmin extends TestSummary {
  questions: QuestionAdmin[];
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

export interface AnswerDetail {
  id: string;
  question_id: string;
  free_text: string | null;
  score: number | null;
  feedback: string | null;
}

export interface AttemptDetail extends Attempt {
  answers: AnswerDetail[];
}

export interface AvailableTest {
  assignment_id: string;
  test_id: string;
  title: string;
  description: string | null;
  due_date: string | null;
  questions_count: number;
}

export interface AttemptHistoryItem {
  attempt_id: string;
  test_id: string;
  test_title: string;
  status: string;
  score: number | null;
  completed_at: string | null;
  started_at: string;
  report_id: string | null;
}

export interface ReportRecommendation {
  topic: string;
  reason: string;
  resource_url?: string | null;
}

export interface ReportItem {
  question_id: string;
  order: number;
  text: string;
  correct_answer: string;
  user_answer: string | null;
  score: number;
  feedback: string | null;
}

export interface ReportParticipant {
  user_id: string;
  email?: string | null;
  full_name?: string | null;
  department?: string | null;
  position?: string | null;
}

export interface Report {
  id: string;
  attempt_id: string;
  user_id: string;
  analysis_id: string;
  score: number;
  data: {
    test?: { title: string; description?: string | null };
    participant?: ReportParticipant;
    items?: ReportItem[];
    recommendations?: ReportRecommendation[];
  };
  created_at: string;
  recommendations: Array<{ id: string; topic: string; resource_url: string | null; reason: string }>;
}

export interface Profile {
  user_id: string;
  email: string;
  full_name: string;
  department: string | null;
  position: string | null;
  role: Role;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Assignment {
  id: string;
  test_id: string;
  user_id: string;
  status: string;
  due_date: string | null;
  assigned_at: string;
  completed_at: string | null;
}

// ----- auth -----

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

export const fetchMe = () => api.get<Me>("/api/v1/users/me").then((r) => r.data);

export const adminResetPassword = (user_id: string, new_password: string) =>
  api.post<{ user_id: string; status: string }>("/api/v1/auth/admin/reset-password", {
    user_id,
    new_password,
  }).then((r) => r.data);

// ----- tests -----

export const listTests = (params?: { active_only?: boolean }) =>
  api
    .get<{ items: TestSummary[]; total: number }>("/api/v1/tests", { params })
    .then((r) => r.data);

export const getTest = (id: string) => api.get<Test | TestAdmin>(`/api/v1/tests/${id}`).then((r) => r.data);

export const createTest = (payload: {
  title: string;
  description?: string | null;
  questions: Array<{ order: number; text: string; correct_answer: string; weight?: number }>;
}) => api.post<TestAdmin>("/api/v1/tests", payload).then((r) => r.data);

export const updateTest = (
  id: string,
  payload: Partial<{
    title: string;
    description: string | null;
    is_active: boolean;
    questions: Array<{ order: number; text: string; correct_answer: string; weight?: number }>;
  }>,
) => api.patch<TestAdmin>(`/api/v1/tests/${id}`, payload).then((r) => r.data);

export const deleteTest = (id: string) =>
  api.delete(`/api/v1/tests/${id}`).then(() => undefined);

// ----- attempts -----

export const startAttempt = (testId: string) =>
  api.post<Attempt>(`/api/v1/tests/${testId}/start`).then((r) => r.data);

export const postAnswers = (
  attemptId: string,
  answers: Array<{ question_id: string; free_text?: string }>,
) =>
  api.post<Attempt>(`/api/v1/attempts/${attemptId}/answers`, { answers }).then((r) => r.data);

export const submitAttempt = (attemptId: string) =>
  api
    .post<{ attempt_id: string; report_id: string | null; status: string; score: number | null }>(
      `/api/v1/attempts/${attemptId}/submit`,
    )
    .then((r) => r.data);

export const getAttempt = (attemptId: string) =>
  api.get<AttemptDetail>(`/api/v1/attempts/${attemptId}`).then((r) => r.data);

export const listAttempts = (params?: { user_id?: string; test_id?: string }) =>
  api
    .get<{ items: Attempt[]; total: number }>("/api/v1/attempts", { params })
    .then((r) => r.data);

export const myHistory = () =>
  api
    .get<{ items: AttemptHistoryItem[]; total: number }>("/api/v1/attempts/me/history")
    .then((r) => r.data);

// ----- assignments -----

export const myAssignments = () =>
  api.get<{ items: AvailableTest[] }>("/api/v1/assignments/me").then((r) => r.data);

export const assignTest = (payload: {
  test_id: string;
  user_ids: string[];
  due_date?: string | null;
}) => api.post<Assignment[]>("/api/v1/assignments", payload).then((r) => r.data);

export const listAssignmentsForTest = (testId: string) =>
  api.get<Assignment[]>(`/api/v1/tests/${testId}/assignments`).then((r) => r.data);

export const revokeAssignment = (assignmentId: string) =>
  api.delete(`/api/v1/assignments/${assignmentId}`).then(() => undefined);

// ----- reports -----

export const getReport = (id: string) => api.get<Report>(`/api/v1/reports/${id}`).then((r) => r.data);

export const reportDownloadUrl = (id: string, format: "pdf" | "html" | "json" = "pdf") =>
  `${baseURL}/api/v1/reports/${id}/download?format=${format}`;

export async function downloadReportPdf(id: string): Promise<Blob> {
  const r = await api.get(`/api/v1/reports/${id}/download`, {
    params: { format: "pdf" },
    responseType: "blob",
  });
  return r.data;
}

// ----- users (admin) -----

export const listUsers = () =>
  api.get<{ items: Profile[]; total: number }>("/api/v1/users").then((r) => r.data);

export const getUser = (id: string) => api.get<Profile>(`/api/v1/users/${id}`).then((r) => r.data);

export const patchUser = (id: string, payload: Partial<{
  full_name: string;
  department: string | null;
  position: string | null;
  role: Role;
  is_active: boolean;
}>) => api.patch<Profile>(`/api/v1/users/${id}`, payload).then((r) => r.data);

export const deactivateUser = (id: string) =>
  api.delete<Profile>(`/api/v1/users/${id}`).then((r) => r.data);
