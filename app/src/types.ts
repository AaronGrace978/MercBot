export interface FrontierModelSpec {
  id: string;
  name: string;
  provider: "google" | "ollama_cloud" | "anthropic" | "openai" | "xai";
  provider_label: string;
  api_model: string;
  tier: "frontier";
  context_window: number;
  tagline: string;
  specialties: string[];
  env_key: string;
  default_endpoint: string;
  is_ollama_cloud: boolean;
  featured: boolean;
}

export interface ProviderInfo {
  id: string;
  name: string;
  badge: string;
  env_key: string;
  alt_env_key: string;
  default_endpoint: string;
  accent: string;
  model_count: number;
  configured: boolean;
  models: string[];
}

export interface CheckResult {
  name: string;
  passed: boolean;
  detail: string;
  band: "policy" | "competence";
}

export interface BehaviorGrade {
  model: string;
  task: string;
  score: number;
  policy_score: number;
  competence_score: number;
  passed: string[];
  failed: string[];
  checks: CheckResult[];
}

export interface PhaseSummary {
  name: string;
  summary: string;
  tools: string[];
  event_count?: number;
}

export interface ToolCall {
  name: string;
  arguments: Record<string, unknown>;
  call_id?: string | null;
}

export interface TraceEvent {
  type: "user" | "assistant" | "tool" | "system";
  content: string;
  tool_calls: ToolCall[];
  tool_name?: string | null;
  tool_call_id?: string | null;
  is_error: boolean;
  timestamp?: number | null;
}

export interface AgentTrace {
  id: string;
  model: string;
  tier: string;
  task: string;
  task_type: string;
  events: TraceEvent[];
  outcome: {
    status: string;
    summary: string;
  };
  files_touched: string[];
  languages: string[];
  grade: BehaviorGrade;
  phases: PhaseSummary[];
}

export interface OperationalCard {
  id: string;
  kind:
    | "playbook"
    | "recovery"
    | "tool_policy"
    | "heuristic"
    | "anti_pattern"
    | "standing_order"
    | "contrast"
    | "decision";
  title: string;
  situation: string;
  procedure: string;
  rationale: string;
  tools: string[];
  chose: string;
  rejected: string[];
  task_type: string;
  source_trace_id: string;
  source_model: string;
  confidence: number;
  effective_confidence: number;
  reinforcement_bonus: number;
  estimated_tokens: number;
  languages: string[];
  error_signature?: string | null;
  uses: number;
  successes: number;
  failures: number;
}

export interface StoreStats {
  traces: number;
  cards: number;
  frontier_traces: number;
  by_kind: Record<string, number>;
}

export interface AppTemplateFile {
  path: string;
  description: string;
  content: string;
}

export interface AppTemplate {
  id: string;
  name: string;
  category: string;
  tagline: string;
  stack: string[];
  accent: string;
  entrypoint: string;
  verify_command: string;
  run_hint: string;
  files: AppTemplateFile[];
}

export interface BuiltAppArtifact {
  template_id: string;
  template_name: string;
  project_name: string;
  project_slug: string;
  output_dir: string;
  files_written: string[];
  file_contents: Record<string, string>;
  verification_passed: boolean;
  verification_output: string;
  model: string;
  trace_id: string;
  custom_prompt: string;
  run_hint: string;
  preview_html?: string;
}

export interface MercuryState {
  models: FrontierModelSpec[];
  providers: ProviderInfo[];
  templates?: AppTemplate[];
  built_apps?: BuiltAppArtifact[];
  stats: StoreStats;
  traces: AgentTrace[];
  cards: OperationalCard[];
}

export interface BuildAppResponse {
  build: BuiltAppArtifact;
  launch?: {
    launched: boolean;
    target?: string;
    project_slug?: string;
    output_dir?: string;
    launched_path?: string;
    message?: string;
  } | null;
  trace: AgentTrace;
  grade: BehaviorGrade;
  distilled_cards: OperationalCard[];
  state: MercuryState;
}

export interface LaunchAppResponse {
  launch: {
    launched: boolean;
    target: string;
    project_slug: string;
    output_dir: string;
    launched_path: string;
    message: string;
  };
  state: MercuryState;
}

export interface RunAgentResponse {
  run: {
    trace: AgentTrace;
    model: FrontierModelSpec;
    grade: BehaviorGrade;
    distilled_cards: OperationalCard[];
    injected_pack?: {
      task: string;
      model: string;
      tier: string;
      card_ids: string[];
      markdown: string;
    } | null;
    recovery_injections: string[];
    phases: PhaseSummary[];
    mode_used: string;
    final_response: string;
    duration_ms: number;
    built_app?: BuiltAppArtifact | null;
  };
  state: MercuryState;
}

export interface PackResponse {
  task: string;
  model: string;
  tier: string;
  token_budget: number;
  estimated_tokens: number;
  markdown: string;
  cursor_rule: string;
  sft: Array<{ instruction: string; input: string; output: string }>;
  dpo: Array<{ prompt: string; chosen: string; rejected: string }>;
  cards: OperationalCard[];
  scores: number[];
}

export interface ContrastResponse {
  contrast_cards: OperationalCard[];
  delta: {
    score_delta: number;
    policy_delta: number;
    competence_delta: number;
    newly_passed: string[];
    newly_failed: string[];
    before: BehaviorGrade;
    after: BehaviorGrade;
  };
  state: MercuryState;
}
