export type FieldErrors = Record<string, string[]>;

export interface ApiErrorBody {
  code: string;
  message: string;
  field_errors: FieldErrors;
  request_id: string;
}

export interface SettingStatus {
  key: string;
  configured: boolean;
  value?: string | null;
  masked_suffix?: string | null;
  updated_at?: string;
}

export interface SettingsResponse {
  settings: SettingStatus[];
}

export interface SettingsUpdate {
  api_key?: string;
  chat_model?: string;
  transcription_model?: string;
  speech_model?: string;
  vision_model?: string;
  voice?: string;
  tts_enabled?: boolean;
  stt_enabled?: boolean;
  theme?: 'system' | 'light' | 'dark';
}

export interface Capability {
  available: boolean;
  reason: string | null;
}

export interface Capabilities {
  interview: Capability;
  speech_to_text: Capability;
  text_to_speech: Capability;
}
