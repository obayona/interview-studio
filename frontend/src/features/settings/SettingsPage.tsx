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
import type {
  Capabilities,
  SettingStatus,
  SettingsUpdate,
} from '../../types/api';
import './settings.css';

const statusValue = (items: SettingStatus[], key: string, fallback = '') =>
  items.find((item) => item.key === key)?.value ?? fallback;

function SettingsForm() {
  const { showToast } = useToast();
  const [statuses, setStatuses] = useState<SettingStatus[]>([]);
  const [capabilities, setCapabilities] = useState<Capabilities>();
  const [form, setForm] = useState<SettingsUpdate>({
    chat_model: 'gpt-4o-mini',
    transcription_model: 'gpt-4o-mini-transcribe',
    speech_model: 'gpt-4o-mini-tts',
    vision_model: 'gpt-4o-mini',
    voice: 'alloy',
    tts_enabled: false,
    stt_enabled: false,
    theme: 'system',
  });
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string>();
  const [removeOpen, setRemoveOpen] = useState(false);
  const [advanced, setAdvanced] = useState(false);

  const apiStatus = useMemo(
    () => statuses.find((item) => item.key === 'api_key'),
    [statuses],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const [settings, nextCapabilities] = await Promise.all([
        settingsApi.get(),
        settingsApi.capabilities(),
      ]);
      setStatuses(settings.settings);
      setCapabilities(nextCapabilities);
      setForm({
        chat_model: statusValue(settings.settings, 'chat_model', 'gpt-4o-mini'),
        transcription_model: statusValue(
          settings.settings,
          'transcription_model',
          'gpt-4o-mini-transcribe',
        ),
        speech_model: statusValue(
          settings.settings,
          'speech_model',
          'gpt-4o-mini-tts',
        ),
        vision_model: statusValue(
          settings.settings,
          'vision_model',
          'gpt-4o-mini',
        ),
        voice: statusValue(settings.settings, 'voice', 'alloy'),
        tts_enabled: statusValue(settings.settings, 'tts_enabled') === 'true',
        stt_enabled: statusValue(settings.settings, 'stt_enabled') === 'true',
        theme: (statusValue(settings.settings, 'theme', 'system') ||
          'system') as SettingsUpdate['theme'],
      });
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : 'Could not load settings.',
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        ...form,
        ...(apiKey.trim() ? { api_key: apiKey.trim() } : {}),
      };
      const response = await settingsApi.update(payload);
      setStatuses(response.settings);
      setApiKey('');
      const nextCapabilities = await settingsApi.capabilities();
      setCapabilities(nextCapabilities);
      applyTheme(form.theme ?? 'system');
      showToast('Settings saved.');
    } catch (requestError) {
      showToast(
        requestError instanceof ApiError
          ? requestError.message
          : 'Settings could not be saved.',
        'error',
      );
    } finally {
      setSaving(false);
    }
  };

  const testConnection = async () => {
    setTesting(true);
    try {
      if (apiKey.trim()) await settingsApi.update({ api_key: apiKey.trim() });
      const result = await settingsApi.testProvider();
      showToast(result.message, result.ok ? 'success' : 'error');
      if (apiKey.trim()) {
        setApiKey('');
        await load();
      }
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
      setStatuses(response.settings);
      setCapabilities(await settingsApi.capabilities());
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
    <>
      {!capabilities?.interview.available && (
        <div className="settings__warning" role="status">
          <Icon name="info" />
          <span>
            {capabilities?.interview.reason}. Interview controls remain
            unavailable until this is resolved.
          </span>
        </div>
      )}
      <div className="settings__grid">
        <Card className="settings__provider">
          <div className="settings__card-heading">
            <span className="settings__provider-icon">
              <Icon name="bolt" />
            </span>
            <div>
              <div className="settings__title-row">
                <h2>OpenAI</h2>
                {apiStatus?.configured && <Badge>Configured</Badge>}
              </div>
              <p>Chat, transcription, speech, and vision models.</p>
            </div>
          </div>
          <FormField
            label="API key"
            htmlFor="api-key"
            hint={
              apiStatus?.configured
                ? `Stored securely · ending in ${apiStatus.masked_suffix}`
                : 'Encrypted locally before it is stored.'
            }
          >
            <Input
              id="api-key"
              type="password"
              autoComplete="off"
              value={apiKey}
              placeholder={
                apiStatus?.configured
                  ? 'Leave blank to keep the current key'
                  : 'sk-…'
              }
              onChange={(event) => setApiKey(event.target.value)}
            />
          </FormField>
          <div className="settings__inline-actions">
            <Button
              onClick={() => void testConnection()}
              disabled={testing || (!apiStatus?.configured && !apiKey.trim())}
            >
              {testing ? 'Testing…' : 'Test connection'}
            </Button>
            {apiStatus?.configured && (
              <Button variant="danger" onClick={() => setRemoveOpen(true)}>
                Remove key
              </Button>
            )}
          </div>
        </Card>

        <Card className="settings__preferences">
          <h2>Interaction preferences</h2>
          <Preference
            label="Voice responses"
            description="Generate spoken interviewer responses."
            checked={Boolean(form.tts_enabled)}
            onChange={(tts_enabled) =>
              setForm((current) => ({ ...current, tts_enabled }))
            }
          />
          <Preference
            label="Speech input"
            description="Transcribe your microphone input."
            checked={Boolean(form.stt_enabled)}
            onChange={(stt_enabled) =>
              setForm((current) => ({ ...current, stt_enabled }))
            }
          />
          <FormField label="Theme" htmlFor="theme">
            <Select
              id="theme"
              value={form.theme}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  theme: event.target.value as SettingsUpdate['theme'],
                }))
              }
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
            setForm={setForm}
          />
          <ModelField
            label="Transcription model"
            name="transcription_model"
            value={form.transcription_model}
            setForm={setForm}
          />
          <ModelField
            label="Speech model"
            name="speech_model"
            value={form.speech_model}
            setForm={setForm}
          />
          <ModelField
            label="Vision model"
            name="vision_model"
            value={form.vision_model}
            setForm={setForm}
          />
          <FormField label="Voice" htmlFor="voice">
            <Select
              id="voice"
              value={form.voice}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  voice: event.target.value,
                }))
              }
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
        <Button onClick={() => void load()}>Discard</Button>
        <Button variant="primary" onClick={() => void save()} disabled={saving}>
          {saving ? 'Saving…' : 'Save changes'}
        </Button>
      </div>
      <Dialog
        open={removeOpen}
        title="Remove OpenAI API key?"
        onClose={() => setRemoveOpen(false)}
        onConfirm={() => void removeKey()}
      >
        <p>
          Interviews and enabled voice features will be unavailable until
          another key is configured.
        </p>
      </Dialog>
    </>
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
  setForm,
}: {
  label: string;
  name: keyof SettingsUpdate;
  value?: string;
  setForm: React.Dispatch<React.SetStateAction<SettingsUpdate>>;
}) {
  return (
    <FormField label={label} htmlFor={name}>
      <Input
        id={name}
        value={value ?? ''}
        onChange={(event) =>
          setForm((current) => ({ ...current, [name]: event.target.value }))
        }
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
