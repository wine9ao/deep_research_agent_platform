import axios, { AxiosProgressEvent } from 'axios';

const api = axios.create({
  baseURL: '/',
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ========== Research APIs ==========

export interface CreateResearchRequest {
  query: string;
  research_type: string;
  use_mock: boolean;
}

export interface CreateResearchResponse {
  task_id: string;
  message: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: string;
  progress: number;       // 0-100
  current_step: string;   // current agent name
  iteration_count: number;
}

export interface AgentStatus {
  name: string;
  display_name: string;
  status: 'pending' | 'active' | 'done';
  description: string;
}

export interface LogEntry {
  timestamp?: string;
  step?: string;
  agent: string;
  action: string;
  details?: string;
  level?: string;
}

export interface ChartData {
  chart_type?: string;
  title: string;
  echarts_option: Record<string, unknown>;
  description?: string;
}

export interface Source {
  title: string;
  source?: string;
  url: string;
  publish_time?: string;
}

export interface QualityScores {
  completeness_score?: number;
  factuality_score?: number;
  logic_score?: number;
  citation_score?: number;
  data_score?: number;
  readability_score?: number;
  final_score?: number;
}

export interface TaskResultResponse {
  task_id: string;
  status?: string;
  final_report: string;
  charts: ChartData[];
  sources: Source[];
  quality_scores: QualityScores;
}

export function createResearch(
  query: string,
  researchType: string,
  useMock: boolean,
): Promise<CreateResearchResponse> {
  return api
    .post<CreateResearchResponse>('/api/research/create', {
      query,
      research_type: researchType,
      use_mock: useMock,
    })
    .then((res) => res.data);
}

export function runResearch(taskId: string): Promise<{ message: string }> {
  return api
    .post<{ message: string }>(`/api/research/run/${taskId}`)
    .then((res) => res.data);
}

export function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  return api
    .get<TaskStatusResponse>(`/api/research/status/${taskId}`)
    .then((res) => res.data);
}

export function getTaskResult(taskId: string): Promise<TaskResultResponse> {
  return api
    .get<TaskResultResponse>(`/api/research/result/${taskId}`)
    .then((res) => res.data);
}

export function getTaskLogs(taskId: string): Promise<LogEntry[]> {
  return api
    .get<LogEntry[]>(`/api/research/logs/${taskId}`)
    .then((res) => res.data);
}

// ========== Knowledge Base APIs ==========

export interface DocumentItem {
  id: string;
  filename: string;
  file_type: string;
  upload_time: string;
  file_size: number;
}

export interface SearchResult {
  content: string;
  source: string;
  score: number;
  metadata: Record<string, unknown>;
}

export function uploadDocument(
  file: File,
  onProgress?: (e: AxiosProgressEvent) => void,
): Promise<{ message: string; document_id: string }> {
  const formData = new FormData();
  formData.append('file', file);
  return api
    .post<
      { message: string; document_id: string }
    >('/api/knowledge/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onProgress,
    })
    .then((res) => res.data);
}

export function listDocuments(): Promise<DocumentItem[]> {
  return api
    .get<DocumentItem[]>('/api/knowledge/documents')
    .then((res) => res.data);
}

export function searchKnowledge(
  query: string,
  topK: number = 5,
  method: string = 'semantic',
): Promise<SearchResult[]> {
  return api
    .post<SearchResult[]>('/api/knowledge/search', {
      query,
      top_k: topK,
      method,
    })
    .then((res) => res.data);
}

// ========== SQL APIs ==========

export interface SQLQueryResponse {
  sql: string;
  result: Record<string, unknown>[];
  explanation: string;
}

export function text2sqlQuery(question: string): Promise<SQLQueryResponse> {
  return api
    .post<SQLQueryResponse>('/api/sql/query', { question })
    .then((res) => res.data);
}

export default api;
