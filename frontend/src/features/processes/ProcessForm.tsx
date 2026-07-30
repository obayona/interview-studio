import { useEffect, useState } from 'react';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { FormField } from '../../components/ui/FormField';
import { Icon } from '../../components/ui/Icon';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { Skeleton } from '../../components/ui/Skeleton';
import { Switch } from '../../components/ui/Switch';
import { ToastProvider, useToast } from '../../components/ui/Toast';
import { useAutosave } from '../../hooks/useAutosave';
import { processApi } from '../../services/process-api';
import { settingsApi } from '../../services/settings-api';
import type {
  ContentSource,
  InterviewProcess,
  ProcessDraft,
  StageConfiguration,
  StageInput,
} from '../../types/process';
import { defaultStages, stageLabels } from './defaults';
import './processes.css';

const emptyDraft = (): ProcessDraft => ({
  title: '',
  company_name: '',
  target_role: '',
  job: { kind: 'text', value: '' },
  company: { kind: 'text', value: '' },
  stages: defaultStages(),
});

const toDraft = (process: InterviewProcess): ProcessDraft => ({
  title: process.title,
  company_name: process.company_name,
  target_role: process.target_role,
  job: process.job_source_url
    ? { kind: 'url', value: process.job_source_url }
    : { kind: 'text', value: process.job_description },
  company: process.company_source_url
    ? { kind: 'url', value: process.company_source_url }
    : { kind: 'text', value: process.company_info },
  stages: process.stages.map(({ id, stage_type, enabled, configuration }) => ({
    id,
    stage_type,
    enabled,
    configuration,
  })),
});

function ProcessFormContent({ mode }: { mode: 'create' | 'edit' }) {
  const { showToast } = useToast();
  const [draft, setDraft] = useState<ProcessDraft>(emptyDraft);
  const [processId, setProcessId] = useState<string>();
  const [loading, setLoading] = useState(mode === 'edit');
  const [creating, setCreating] = useState(false);
  const {
    status: saveStatus,
    valueRef: draftRef,
    track,
    reset,
    saveNow,
  } = useAutosave({
    value: draft,
    enabled: mode === 'edit' && !loading && Boolean(processId),
    persist: (nextDraft) => processApi.update(processId!, nextDraft),
    normalize: toDraft,
    onSaved: (_process, normalized, _submitted, isCurrent, announced) => {
      if (isCurrent) setDraft(normalized);
      if (announced) showToast('Process saved.');
    },
    onError: () => showToast('Process could not be saved.', 'error'),
    onAlreadySaved: () => showToast('Process is already up to date.'),
  });

  useEffect(() => {
    if (mode !== 'create') return;
    settingsApi
      .get()
      .then(({ settings }) => {
        const enabled = (key: string) =>
          settings.find((setting) => setting.key === key)?.value === 'true';
        setDraft((current) => ({
          ...current,
          stages: current.stages.map((stage) => ({
            ...stage,
            configuration: {
              ...stage.configuration,
              media: {
                ...stage.configuration.media,
                speech_to_text: enabled('stt_enabled'),
                text_to_speech: enabled('tts_enabled'),
              },
            },
          })),
        }));
      })
      .catch(() => {
        // Process creation remains available with safe text-only defaults.
      });
  }, [mode]);

  useEffect(() => {
    if (mode !== 'edit') return;
    const id = new URLSearchParams(window.location.search).get('id');
    if (!id) {
      showToast('No process was selected for editing.', 'error');
      setLoading(false);
      return;
    }
    setProcessId(id);
    processApi
      .get(id)
      .then((process) => {
        const loaded = toDraft(process);
        setDraft(loaded);
        reset(loaded);
      })
      .catch(() => showToast('Process could not be loaded.', 'error'))
      .finally(() => setLoading(false));
  }, [mode, reset, showToast]);

  const submit = async () => {
    if (mode === 'edit') {
      await saveNow(draftRef.current, true);
      return;
    }
    setCreating(true);
    try {
      const saved = await processApi.create(draft);
      window.location.href = `/processes/details?id=${encodeURIComponent(saved.id)}`;
    } catch {
      showToast('Process could not be saved.', 'error');
      setCreating(false);
    }
  };

  const updateDraft = (next: ProcessDraft) => {
    track(next);
    setDraft(next);
  };

  const updateStage = (index: number, stage: StageInput) =>
    setDraft((current) => ({
      ...current,
      stages: current.stages.map((item, itemIndex) => {
        const next = itemIndex === index ? stage : item;
        if (itemIndex === current.stages.length - 1) {
          track({
            ...current,
            stages: current.stages.map((candidate, candidateIndex) =>
              candidateIndex === index ? stage : candidate,
            ),
          });
        }
        return next;
      }),
    }));

  const moveStageUp = (index: number) =>
    setDraft((current) => {
      if (index === 0) return current;
      const stages = [...current.stages];
      [stages[index - 1], stages[index]] = [stages[index], stages[index - 1]];
      const next = { ...current, stages };
      track(next);
      return next;
    });

  if (loading) return <Skeleton height="50rem" />;

  return (
    <form
      className="processes__form"
      onBlur={() => {
        if (mode === 'edit') void saveNow(draftRef.current);
      }}
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <div className="processes__form-layout">
        <div className="processes__form-main">
          <Card className="processes__fields">
            <h2>
              <Icon name="briefcase" /> Job essentials
            </h2>
            <div className="processes__field-grid">
              <FormField label="Process title" htmlFor="process-title">
                <Input
                  id="process-title"
                  required
                  value={draft.title}
                  placeholder="Backend role at Acme"
                  onChange={(event) =>
                    updateDraft({ ...draft, title: event.target.value })
                  }
                />
              </FormField>
              <FormField label="Target role" htmlFor="target-role">
                <Input
                  id="target-role"
                  required
                  value={draft.target_role}
                  placeholder="Senior Backend Engineer"
                  onChange={(event) =>
                    updateDraft({ ...draft, target_role: event.target.value })
                  }
                />
              </FormField>
            </div>
            <SourceEditor
              label="Job description"
              source={draft.job}
              required
              onChange={(job) => updateDraft({ ...draft, job })}
            />
          </Card>

          <Card className="processes__fields">
            <h2>Company context</h2>
            <FormField label="Company name" htmlFor="company-name">
              <Input
                id="company-name"
                value={draft.company_name}
                placeholder="Acme"
                onChange={(event) =>
                  updateDraft({ ...draft, company_name: event.target.value })
                }
              />
            </FormField>
            <SourceEditor
              label="Company information"
              source={draft.company ?? { kind: 'text', value: '' }}
              onChange={(company) => updateDraft({ ...draft, company })}
            />
          </Card>
        </div>

        <aside className="processes__stage-list">
          <Card>
            <h2>Interview stages</h2>
            <p className="processes__muted">
              Skipped stages remain visible and can be enabled later.
            </p>
          </Card>
          {draft.stages.map((stage, index) => (
            <StageEditor
              key={stage.id}
              stage={stage}
              index={index}
              onChange={(next) => updateStage(index, next)}
              onMoveUp={() => moveStageUp(index)}
            />
          ))}
        </aside>
      </div>
      <div className="processes__actions">
        <a
          className="ui-button"
          href={
            mode === 'edit' && processId
              ? `/processes/details?id=${encodeURIComponent(processId)}`
              : '/processes'
          }
        >
          Cancel
        </a>
        {mode === 'edit' && (
          <span
            className={`processes__save-status processes__save-status--${saveStatus}`}
          >
            {saveStatus === 'saving'
              ? 'Saving…'
              : saveStatus === 'pending'
                ? 'Unsaved changes'
                : saveStatus === 'error'
                  ? 'Save failed'
                  : 'All changes saved'}
          </span>
        )}
        <Button
          variant="primary"
          type="submit"
          disabled={creating || saveStatus === 'saving'}
        >
          {creating || saveStatus === 'saving'
            ? 'Saving…'
            : mode === 'edit'
              ? 'Save process'
              : 'Create process'}
        </Button>
      </div>
    </form>
  );
}

function SourceEditor({
  label,
  source,
  onChange,
  required = false,
}: {
  label: string;
  source: ContentSource;
  onChange: (source: ContentSource) => void;
  required?: boolean;
}) {
  const { showToast } = useToast();
  const [preview, setPreview] = useState('');
  const [previewing, setPreviewing] = useState(false);

  const previewUrl = async () => {
    setPreviewing(true);
    try {
      const result = await processApi.preview(source.value);
      setPreview(result.content);
    } catch {
      showToast('URL content could not be previewed.', 'error');
    } finally {
      setPreviewing(false);
    }
  };

  return (
    <div className="processes__fields">
      <div className="processes__source-tabs" role="tablist" aria-label={label}>
        {(['text', 'url'] as const).map((kind) => (
          <Button
            key={kind}
            type="button"
            role="tab"
            aria-selected={source.kind === kind}
            onClick={() => {
              setPreview('');
              onChange({ kind, value: '' });
            }}
          >
            {kind === 'text' ? 'Paste text' : 'Import URL'}
          </Button>
        ))}
      </div>
      {source.kind === 'text' ? (
        <FormField label={label} htmlFor={`${label}-text`}>
          <textarea
            id={`${label}-text`}
            className="ui-input processes__textarea"
            required={required}
            value={source.value}
            onChange={(event) =>
              onChange({ kind: 'text', value: event.target.value })
            }
            rows={8}
          />
        </FormField>
      ) : (
        <>
          <FormField label={`${label} URL`} htmlFor={`${label}-url`}>
            <Input
              id={`${label}-url`}
              type="url"
              required={required}
              value={source.value}
              placeholder="https://…"
              onChange={(event) =>
                onChange({ kind: 'url', value: event.target.value })
              }
            />
          </FormField>
          <Button
            type="button"
            disabled={!source.value || previewing}
            onClick={() => void previewUrl()}
          >
            {previewing ? 'Fetching…' : 'Preview imported content'}
          </Button>
          {preview && (
            <div className="processes__preview" aria-label={`${label} preview`}>
              {preview}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function StageEditor({
  stage,
  index,
  onChange,
  onMoveUp,
}: {
  stage: StageInput;
  index: number;
  onChange: (stage: StageInput) => void;
  onMoveUp: () => void;
}) {
  const updateConfiguration = (configuration: StageConfiguration) =>
    onChange({ ...stage, configuration });
  const config = stage.configuration;

  return (
    <Card className="processes__stage">
      <div className="processes__stage-heading">
        <div>
          <h3>
            {index + 1}. {stageLabels[stage.stage_type]}
          </h3>
          <small>{stage.enabled ? 'Included' : 'Skipped'}</small>
        </div>
        <div className="processes__stage-actions">
          <Button
            type="button"
            onClick={onMoveUp}
            disabled={index === 0}
            aria-label={`Move ${stageLabels[stage.stage_type]} up`}
          >
            <Icon name="arrowUp" />
          </Button>
          <Switch
            label={`Include ${stageLabels[stage.stage_type]}`}
            checked={stage.enabled}
            onChange={(enabled) => onChange({ ...stage, enabled })}
          />
        </div>
      </div>
      <details>
        <summary>Configure stage</summary>
        <div className="processes__stage-config">
          <div className="processes__config-grid">
            <FormField label="Difficulty" htmlFor={`difficulty-${stage.id}`}>
              <Select
                id={`difficulty-${stage.id}`}
                value={config.difficulty}
                onChange={(event) =>
                  updateConfiguration({
                    ...config,
                    difficulty: event.target
                      .value as StageConfiguration['difficulty'],
                  })
                }
              >
                <option value="junior">Junior</option>
                <option value="mid">Mid-level</option>
                <option value="senior">Senior</option>
                <option value="staff">Staff</option>
              </Select>
            </FormField>
            <FormField label="Interviewer" htmlFor={`interviewer-${stage.id}`}>
              <Select
                id={`interviewer-${stage.id}`}
                value={config.interviewer_profile}
                onChange={(event) =>
                  updateConfiguration({
                    ...config,
                    interviewer_profile: event.target
                      .value as StageConfiguration['interviewer_profile'],
                  })
                }
              >
                <option value="hr_recruiter">HR recruiter</option>
                <option value="tech_lead">Tech lead</option>
                <option value="engineering_manager">Engineering manager</option>
                <option value="cto">CTO</option>
                <option value="ceo">CEO</option>
                <option value="peer_engineer">Peer engineer</option>
              </Select>
            </FormField>
            <FormField label="Language" htmlFor={`language-${stage.id}`}>
              <Input
                id={`language-${stage.id}`}
                value={config.language}
                onChange={(event) =>
                  updateConfiguration({
                    ...config,
                    language: event.target.value,
                  })
                }
              />
            </FormField>
            <FormField label="Topics" htmlFor={`topics-${stage.id}`}>
              <Input
                id={`topics-${stage.id}`}
                value={config.topics.join(', ')}
                onChange={(event) =>
                  updateConfiguration({
                    ...config,
                    topics: event.target.value
                      .split(',')
                      .map((value) => value.trim())
                      .filter(Boolean),
                  })
                }
              />
            </FormField>
            <NumberField
              label="Questions"
              id={`questions-${stage.id}`}
              min={1}
              max={100}
              value={config.limits.max_questions}
              onChange={(max_questions) =>
                updateConfiguration({
                  ...config,
                  limits: { ...config.limits, max_questions },
                })
              }
            />
            <NumberField
              label="Minutes"
              id={`minutes-${stage.id}`}
              min={1}
              max={240}
              value={config.limits.max_duration_minutes}
              onChange={(max_duration_minutes) =>
                updateConfiguration({
                  ...config,
                  limits: { ...config.limits, max_duration_minutes },
                })
              }
            />
            <NumberField
              label="Follow-ups per topic"
              id={`followups-${stage.id}`}
              min={0}
              max={3}
              value={config.limits.follow_up_questions_per_topic}
              onChange={(follow_up_questions_per_topic) =>
                updateConfiguration({
                  ...config,
                  limits: {
                    ...config.limits,
                    follow_up_questions_per_topic,
                  },
                })
              }
            />
          </div>
          <FormField
            label="Optional instructions"
            htmlFor={`notes-${stage.id}`}
          >
            <textarea
              id={`notes-${stage.id}`}
              className="ui-input"
              value={config.user_instructions}
              onChange={(event) =>
                updateConfiguration({
                  ...config,
                  user_instructions: event.target.value,
                })
              }
            />
          </FormField>
          {(
            [
              ['text_input', 'Text input'],
              ['text_output', 'Text responses'],
              ['speech_to_text', 'Speech input'],
              ['text_to_speech', 'Voice responses'],
              ['natural_interruptions', 'Natural interruptions'],
            ] as const
          ).map(([key, label]) => (
            <div className="processes__stage-heading" key={key}>
              <span>{label}</span>
              <Switch
                label={label}
                checked={config.media[key]}
                onChange={(checked) =>
                  updateConfiguration({
                    ...config,
                    media: { ...config.media, [key]: checked },
                  })
                }
              />
            </div>
          ))}
        </div>
      </details>
    </Card>
  );
}

function NumberField({
  label,
  id,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  id: string;
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
}) {
  return (
    <FormField label={label} htmlFor={id}>
      <Input
        id={id}
        type="number"
        min={min}
        max={max}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </FormField>
  );
}

export function ProcessForm({ mode }: { mode: 'create' | 'edit' }) {
  return (
    <ToastProvider>
      <ProcessFormContent mode={mode} />
    </ToastProvider>
  );
}
