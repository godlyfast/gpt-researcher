export interface BaseData {
  type: string;
}

export interface BasicData extends BaseData {
  type: 'basic';
  content: string;
}

export interface LanggraphButtonData extends BaseData {
  type: 'langgraphButton';
  link: string;
}

export interface DifferencesData extends BaseData {
  type: 'differences';
  content: string;
  output: string;
}

export interface QuestionData extends BaseData {
  type: 'question';
  content: string;
}

export interface ChatData extends BaseData {
  type: 'chat';
  content: string;
}

export interface ErrorData extends BaseData {
  type: 'error';
  content: string;
  output: string;
}

export interface ReportData extends BaseData {
  type: 'report';
  content?: string;
  output: string;
}

export interface LogsData extends BaseData {
  type: 'logs';
  content: string;
  output: string;
  metadata?: any;
}

export interface GenericData extends BaseData {
  type: string;
  content?: string;
  output?: string;
  metadata?: any;
}

export type Data = BasicData | LanggraphButtonData | DifferencesData | QuestionData | ChatData | ErrorData | ReportData | LogsData | GenericData;

export interface ChatBoxSettings {
  report_type: string;
  report_source: string;
  tone: string;
  domains: string[];
  defaultReportType: string;
  mcp_enabled: boolean;
  mcp_configs: MCPConfig[];
}

export interface MCPConfig {
  name: string;
  command: string;
  args: string[];
  env: Record<string, string>;
}

export interface Domain {
  value: string;
}

export interface ResearchHistoryItem {
  id: string;
  question: string;
  answer: string;
  timestamp: number;
  orderedData: Data[];
} 