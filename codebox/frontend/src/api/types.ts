export type Status =
  | "QUEUED"
  | "RUNNING"
  | "COMPLETED"
  | "TIME_LIMIT_EXCEEDED"
  | "MEMORY_LIMIT_EXCEEDED"
  | "COMPILATION_ERROR"
  | "RUNTIME_ERROR"
  | "FAILED"
  | "ACCEPTED"
  | "WRONG_ANSWER";

export interface User {
  id: number;
  username: string;
  email: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Language {
  key: string;
  name: string;
  monaco: string;
  time_limit_seconds: number;
}

export interface LanguagesResponse {
  languages: Language[];
  limits: { memory: string; cpus: number; timeout_seconds: number };
}

export interface ProblemSummary {
  id: number;
  slug: string;
  title: string;
  difficulty: "Easy" | "Medium" | "Hard";
  tags: string[];
  solved: boolean;
  /** Submitted at least once but not solved yet. */
  attempted: boolean;
  /** Judged submissions by all users. */
  submissions: number;
  /** Accepted / submissions (0..1), or null when nobody has submitted. */
  acceptance_rate: number | null;
}

export interface ProblemDetail extends ProblemSummary {
  description: string;
  constraints: string;
  examples: { input: string; output: string; explanation?: string | null }[];
  starter_code: Record<string, string>;
  test_case_count: number;
}

export interface ExecutionAccepted {
  execution_id: string;
  submission_id: number;
  status: Status;
}

export interface TestResult {
  index: number;
  passed: boolean;
  status: Status;
  time_ms: number;
  memory_kb: number;
  is_sample: boolean;
  message?: string | null;
  input?: string | null;
  expected_output?: string | null;
  actual_output?: string | null;
  stderr?: string | null;
}

export interface ExecutionResult {
  execution_id: string;
  submission_id: number;
  kind: "run" | "submit";
  language: string;
  status: Status;
  stdout: string | null;
  stderr: string | null;
  compile_output: string | null;
  execution_time: number | null;
  memory_used: number | null;
  passed_count: number | null;
  total_count: number | null;
  test_results: TestResult[] | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface SubmissionSummary {
  id: number;
  execution_id: string | null;
  kind: "run" | "submit";
  problem_id: number | null;
  problem_title: string | null;
  language: string;
  status: Status;
  execution_time: number | null;
  memory_used: number | null;
  passed_count: number | null;
  total_count: number | null;
  created_at: string;
}

export interface SubmissionList {
  items: SubmissionSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface SubmissionDetail extends SubmissionSummary {
  source_code: string;
  stdin: string;
  stdout: string | null;
  stderr: string | null;
  compile_output: string | null;
  test_results: TestResult[] | null;
  error_message: string | null;
}

export type AIAction = "auto" | "explain" | "debug" | "complexity" | "optimize";

export interface AIRequest {
  action: AIAction;
  language: string;
  source_code: string;
  question?: string;
  error?: string;
  stdin?: string;
  stdout?: string;
  problem_id?: number;
}

export interface AIResponse {
  agent: string;
  content: string;
  model: string;
}
