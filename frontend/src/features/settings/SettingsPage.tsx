import { useCallback, useEffect, useMemo, useState } from 'react';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Dialog } from '../../components/ui/Dialog';
import { FormField } from '../../components/ui/FormField';
import { Icon } from '../../components/ui/Icon';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { Skeleton } from '../../components/ui/Skeleton';
import { ErrorState } from '../../components/ui/States';
import { Switch } from '../../components/ui/Switch';
import { ToastProvider, useToast } from '../../components/ui/Toast';
import { ApiError } from '../../services/api-client';
import { settingsApi } from '../../services/settings-api';
import { useAutosave } from '../../hooks/useAutosave';
import type { SettingStatus, SettingsUpdate } from '../../types/api';
import './settings.css';

const statusValue = (items: SettingStatus[], key: string, fallback = '') =>
  items.find((item) => item.key === key)?.value ?? fallback;

const settingsToForm = (settings: SettingStatus[]): SettingsUpdate => ({
  api_key: '',
  chat_model: statusValue(settings, 'chat_model', 'gpt-4o-mini'),
  transcription_model: statusValue(
    settings,
    'transcription_model',
    'gpt-4o-mini-transcribe',
  ),
  speech_model: statusValue(settings, 'speech_model', 'gpt-4o-mini-tts'),
  vision_model: statusValue(settings, 'vision_model', 'gpt-4o-mini'),
  voice: statusValue(settings, 'voice', 'alloy'),
  tts_enabled: statusValue(settings, 'tts_enabled') === 'true',
  stt_enabled: statusValue(settings, 'stt_enabled') === 'true',
  theme: (statusValue(settings, 'theme', 'system') ||
    'system') as SettingsUpdate['theme'],
});

function SettingsForm() {
  const { showToast } = useToast();
  const [statuses, setStatuses] = useState<SettingStatus[]>([]);
  const [form, setForm] = useState<SettingsUpdate>({
    api_key: '',
    chat_model: 'gpt-4o-mini',
    transcription_model: 'gpt-4o-mini-transcribe',
    speech_model: 'gpt-4o-mini-tts',
    vision_model: 'gpt-4o-mini',
    voice: 'alloy',
    tts_enabled: false,
    stt_enabled: false,
    theme: 'system',
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [advanced, setAdvanced] = useState(false);
  const {
    status: saveStatus,
    valueRef: formRef,
    track,
    reset,
    saveNow: save,
  } = useAutosave({
    value: form,
    enabled: !loading,
    persist: async (nextForm) => {
      const nextApiKey = nextForm.api_key?.trim();
      const payload = {
        ...nextForm,
        ...(nextApiKey ? { api_key: nextApiKey } : {}),
      };
      if (!nextApiKey) delete payload.api_key;
      const response = await settingsApi.update(payload);
      return {
        response,
        form: settingsToForm(response.settings),
      };
    },
    normalize: (result) => result.form,
    onSaved: (result, normalized, submitted, isCurrent, announced) => {
      setStatuses(result.response.settings);
      if (isCurrent) setForm(normalized);
      applyTheme(submitted.theme ?? 'system');
      if (announced) showToast('Settings saved.');
    },
    onError: (requestError) =>
      showToast(
        requestError instanceof ApiError
          ? requestError.message
          : 'Settings could not be saved.',
        'error',
      ),
    onAlreadySaved: () => showToast('Settings are already up to date.'),
  });

  const apiStatus = useMemo(
    () => statuses.find((item) => item.key === 'api_key'),
    [statuses],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const settings = await settingsApi.get();
      setStatuses(settings.settings);
      const nextForm = settingsToForm(settings.settings);
      setForm(nextForm);
      reset(nextForm);
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : 'Could not load settings.',
      );
    } finally {
      setLoading(false);
    }
  }, [reset]);

  useEffect(() => {
    void load();
  }, [load]);

  const update = <Key extends keyof SettingsUpdate>(
    key: Key,
    value: SettingsUpdate[Key],
  ) => {
    const next = { ...formRef.current, [key]: value };
    track(next);
    setForm(next);
  };

  if (loading) {
    return (
      <div className="settings__loading" aria-label="Loading settings">
        <Skeleton height="24rem" />
        <Skeleton height="24rem" />
      </div>
    );
  }
  if (error) return <ErrorState message={error} onRetry={() => void load()} />;

  return (
    <div
      className="settings__form"
      onBlur={(event) => {
        if (
          (event.relatedTarget as HTMLElement | null)?.closest(
            '[data-settings-save]',
          )
        )
          return;
        void save(formRef.current);
      }}
    >
      <div className="settings__grid">
        <APIKeyField
          status={apiStatus}
          value={form.api_key ?? ''}
          saving={saveStatus === 'saving'}
          onChange={(api_key) => update('api_key', api_key)}
          onSave={() => save(formRef.current)}
          onSettingsChange={(settings) => {
            setStatuses(settings);
            const next = { ...formRef.current, api_key: '' };
            track(next);
            setForm(next);
          }}
        />

        <Card className="settings__preferences">
          <h2>Interaction preferences</h2>
          <Preference
            label="Voice responses"
            description="Generate spoken interviewer responses."
            checked={Boolean(form.tts_enabled)}
            onChange={(tts_enabled) => update('tts_enabled', tts_enabled)}
          />
          <Preference
            label="Speech input"
            description="Transcribe your microphone input."
            checked={Boolean(form.stt_enabled)}
            onChange={(stt_enabled) => update('stt_enabled', stt_enabled)}
          />
          <FormField label="Theme" htmlFor="theme">
            <Select
              id="theme"
              value={form.theme}
              onChange={(event) => {
                const theme = event.target.value as NonNullable<
                  SettingsUpdate['theme']
                >;
                applyTheme(theme);
                update('theme', theme);
              }}
            >
              <option value="system">Follow system</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </Select>
          </FormField>
        </Card>
      </div>

      <button
        className="settings__advanced-toggle"
        type="button"
        aria-expanded={advanced}
        onClick={() => setAdvanced((value) => !value)}
      >
        <Icon name="settings" /> Advanced model parameters
      </button>
      {advanced && (
        <Card className="settings__advanced">
          <ModelField
            label="Chat model"
            name="chat_model"
            value={form.chat_model}
            onChange={(value) => update('chat_model', value)}
          />
          <ModelField
            label="Transcription model"
            name="transcription_model"
            value={form.transcription_model}
            onChange={(value) => update('transcription_model', value)}
          />
          <ModelField
            label="Speech model"
            name="speech_model"
            value={form.speech_model}
            onChange={(value) => update('speech_model', value)}
          />
          <ModelField
            label="Vision model"
            name="vision_model"
            value={form.vision_model}
            onChange={(value) => update('vision_model', value)}
          />
          <FormField label="Voice" htmlFor="voice">
            <Select
              id="voice"
              value={form.voice}
              onChange={(event) => update('voice', event.target.value)}
            >
              {[
                'alloy',
                'ash',
                'ballad',
                'coral',
                'echo',
                'fable',
                'nova',
                'onyx',
                'sage',
                'shimmer',
                'verse',
              ].map((voice) => (
                <option key={voice} value={voice}>
                  {voice}
                </option>
              ))}
            </Select>
          </FormField>
        </Card>
      )}
      <div className="settings__actions">
        <span aria-live="polite">
          {saveStatus === 'pending' && 'Changes pending'}
          {saveStatus === 'saved' && 'All changes saved'}
          {saveStatus === 'error' && 'Save failed'}
        </span>
        <Button
          variant="primary"
          onClick={() => void save(formRef.current, true)}
          disabled={saveStatus === 'saving'}
          data-settings-save
        >
          {saveStatus === 'saving' ? 'Saving…' : 'Save changes'}
        </Button>
      </div>
    </div>
  );
}

function APIKeyField({
  status,
  value,
  saving,
  onChange,
  onSave,
  onSettingsChange,
}: {
  status?: SettingStatus;
  value: string;
  saving: boolean;
  onChange: (value: string) => void;
  onSave: () => Promise<boolean>;
  onSettingsChange: (settings: SettingStatus[]) => void;
}) {
  const { showToast } = useToast();
  const [testing, setTesting] = useState(false);
  const [removeOpen, setRemoveOpen] = useState(false);
  const configured = Boolean(status?.configured);

  const testConnection = async () => {
    setTesting(true);
    try {
      const apiKey = value.trim();
      if (apiKey) await onSave();
      const result = await settingsApi.testProvider();
      showToast(result.message, result.ok ? 'success' : 'error');
    } catch (requestError) {
      showToast(
        requestError instanceof ApiError
          ? requestError.message
          : 'Connection test failed.',
        'error',
      );
    } finally {
      setTesting(false);
    }
  };

  const removeKey = async () => {
    try {
      const response = await settingsApi.remove('api_key');
      onSettingsChange(response.settings);
      setRemoveOpen(false);
      showToast('OpenAI API key removed.');
    } catch (requestError) {
      showToast(
        requestError instanceof ApiError
          ? requestError.message
          : 'The API key was not removed.',
        'error',
      );
    }
  };

  return (
    <Card className="settings__provider">
      <div className="settings__card-heading">
        <span className="settings__provider-icon">
          <Icon name="bolt" />
        </span>
        <div>
          <div className="settings__title-row">
            <h2>OpenAI</h2>
            {configured && <Badge>Configured</Badge>}
          </div>
          <p>Chat, transcription, speech, and vision models.</p>
        </div>
      </div>
      <FormField
        label="API key"
        htmlFor="api-key"
        hint={
          configured
            ? `Stored securely · ending in ${status?.masked_suffix}`
            : 'Encrypted locally before it is stored.'
        }
      >
        <Input
          id="api-key"
          type="password"
          autoComplete="off"
          value={value}
          placeholder={configured ? '********' : 'sk-…'}
          onChange={(event) => onChange(event.target.value)}
        />
      </FormField>
      <div className="settings__inline-actions">
        <Button
          onClick={() => void testConnection()}
          disabled={saving || testing || (!configured && !value.trim())}
          data-settings-save
        >
          {testing ? 'Testing…' : 'Test connection'}
        </Button>
        {configured && (
          <Button
            variant="danger"
            onClick={() => setRemoveOpen(true)}
            data-settings-save
          >
            Remove key
          </Button>
        )}
      </div>
      <Dialog open={removeOpen} onClose={() => setRemoveOpen(false)}>
        <div className="ui-dialog__content">
          <h2>Remove OpenAI API key?</h2>
          <p>
            Interviews and enabled voice features will be unavailable until
            another key is configured.
          </p>
          <div className="ui-dialog__actions">
            <Button onClick={() => setRemoveOpen(false)}>Cancel</Button>
            <Button variant="primary" onClick={() => void removeKey()}>
              Confirm
            </Button>
          </div>
        </div>
      </Dialog>
    </Card>
  );
}

function Preference({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <div className="settings__preference">
      <div>
        <strong>{label}</strong>
        <p>{description}</p>
      </div>
      <Switch label={label} checked={checked} onChange={onChange} />
    </div>
  );
}

function ModelField({
  label,
  name,
  value,
  onChange,
}: {
  label: string;
  name: keyof SettingsUpdate;
  value?: string;
  onChange: (value: string) => void;
}) {
  return (
    <FormField label={label} htmlFor={name}>
      <Input
        id={name}
        value={value ?? ''}
        onChange={(event) => onChange(event.target.value)}
      />
    </FormField>
  );
}

function applyTheme(theme: NonNullable<SettingsUpdate['theme']>) {
  localStorage.setItem('interview-studio-theme', theme);
  if (theme === 'system') delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = theme;
}

export function SettingsPage() {
  return (
    <ToastProvider>
      <SettingsForm />
    </ToastProvider>
  );
}
