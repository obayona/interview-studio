import {
  Fragment,
  useCallback,
  useEffect,
  useState,
  type ChangeEvent,
  type ReactNode,
} from 'react';
import { announceProfileUpdate } from '../../components/layout/HeaderAvatar';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Dialog } from '../../components/ui/Dialog';
import { FormField } from '../../components/ui/FormField';
import { Icon } from '../../components/ui/Icon';
import { Input } from '../../components/ui/Input';
import { Skeleton } from '../../components/ui/Skeleton';
import { Spinner } from '../../components/ui/Spinner';
import { ErrorState } from '../../components/ui/States';
import { ToastProvider, useToast } from '../../components/ui/Toast';
import { ApiError } from '../../services/api-client';
import { profileApi } from '../../services/profile-api';
import { useAutosave, type SaveStatus } from '../../hooks/useAutosave';
import type {
  DeveloperProfile,
  ProfileDraft,
  ProfileLinkType,
  ProfileProject,
  ProfileSuggestions,
  WorkExperience,
} from '../../types/profile';
import './profile.css';

const emptyDraft: ProfileDraft = {
  full_name: '',
  headline: '',
  summary: '',
  location: '',
  email: '',
  phone: '',
  skills: [],
  seniority: '',
  availability: '',
  links: [],
  experiences: [],
  projects: [],
};

const toDraft = (profile: DeveloperProfile): ProfileDraft => ({
  full_name: profile.full_name,
  headline: profile.headline,
  summary: profile.summary,
  location: profile.location,
  email: profile.email,
  phone: profile.phone,
  skills: profile.skills,
  seniority: profile.seniority,
  availability: profile.availability,
  links: profile.links,
  experiences: profile.experiences,
  projects: profile.projects,
});

const newId = () => crypto.randomUUID();
const applyImport = (
  current: ProfileDraft,
  suggestions: ProfileSuggestions,
): ProfileDraft => ({
  ...current,
  full_name: suggestions.full_name ?? current.full_name,
  headline: suggestions.headline ?? current.headline,
  summary: suggestions.summary ?? current.summary,
  location: suggestions.location ?? current.location,
  email: suggestions.email ?? current.email,
  phone: suggestions.phone ?? current.phone,
  skills: suggestions.skills.length ? suggestions.skills : current.skills,
  experiences: suggestions.experiences.length
    ? suggestions.experiences
    : current.experiences,
  projects: suggestions.projects.length
    ? suggestions.projects
    : current.projects,
});

function ProfileForm() {
  const { showToast } = useToast();
  const [profile, setProfile] = useState<DeveloperProfile>();
  const [draft, setDraft] = useState<ProfileDraft>(emptyDraft);
  const [importOpen, setImportOpen] = useState(false);
  const [selectedCV, setSelectedCV] = useState<File>();
  const [loading, setLoading] = useState(true);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [cvProcessing, setCVProcessing] = useState(false);
  const [error, setError] = useState<string>();
  const {
    status: saveStatus,
    valueRef: draftRef,
    track,
    reset,
    saveNow: save,
  } = useAutosave({
    value: draft,
    enabled: !loading,
    persist: profileApi.update,
    normalize: toDraft,
    onSaved: (saved, _normalized, _submitted, _isCurrent, announced) => {
      setProfile(saved);
      announceProfileUpdate(saved);
      if (announced) showToast('Profile saved.');
    },
    onError: (requestError) =>
      showToast(
        messageFor(requestError, 'Profile could not be saved.'),
        'error',
      ),
    onAlreadySaved: () => showToast('Profile is already up to date.'),
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const nextProfile = await profileApi.get();
      const nextDraft = toDraft(nextProfile);
      setProfile(nextProfile);
      announceProfileUpdate(nextProfile);
      setDraft(nextDraft);
      reset(nextDraft);
    } catch (requestError) {
      setError(messageFor(requestError, 'Could not load the profile.'));
    } finally {
      setLoading(false);
    }
  }, [reset]);

  useEffect(() => {
    void load();
  }, [load]);

  const update = <Key extends keyof ProfileDraft>(
    key: Key,
    value: ProfileDraft[Key],
  ) =>
    setDraft((current) => {
      const next = { ...current, [key]: value };
      track(next);
      return next;
    });

  const updateLink = (type: ProfileLinkType, url: string) => {
    const existing = draft.links.find((link) => link.link_type === type);
    const remaining = draft.links.filter((link) => link.link_type !== type);
    update(
      'links',
      url
        ? [
            ...remaining,
            {
              id: existing?.id ?? newId(),
              link_type: type,
              url,
              position: remaining.length,
            },
          ]
        : remaining,
    );
  };

  const uploadAvatar = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setAvatarUploading(true);
    try {
      const nextProfile = await profileApi.uploadAvatar(file);
      setProfile(nextProfile);
      announceProfileUpdate(nextProfile);
      showToast('Profile photo updated.');
    } catch (requestError) {
      showToast(messageFor(requestError, 'Photo upload failed.'), 'error');
    } finally {
      setAvatarUploading(false);
    }
  };

  const importCV = async () => {
    if (!selectedCV) return;
    setCVProcessing(true);
    try {
      const suggestions = await profileApi.importCV(selectedCV);
      const nextDraft = applyImport(draftRef.current, suggestions);
      track(nextDraft);
      setDraft(nextDraft);
      if (!(await save(nextDraft))) return;
      setImportOpen(false);
      setSelectedCV(undefined);
      showToast('CV details imported.');
    } catch (requestError) {
      showToast(messageFor(requestError, 'CV import failed.'), 'error');
    } finally {
      setCVProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="profile__loading" aria-label="Loading profile">
        <Skeleton height="30rem" />
        <Skeleton height="42rem" />
      </div>
    );
  }
  if (error) return <ErrorState message={error} onRetry={() => void load()} />;

  return (
    <>
      <div className="profile__toolbar">
        <SaveStatus status={saveStatus} />
        <Button onClick={() => setImportOpen(true)}>
          <Icon name="upload" />
          Import CV
        </Button>
        <Button
          variant="primary"
          onClick={() => void save(draftRef.current, true)}
          disabled={saveStatus === 'saving'}
          data-profile-save
        >
          {saveStatus === 'saving' ? 'Saving…' : 'Save profile'}
        </Button>
      </div>

      <div
        className="profile__layout"
        onBlur={(event) => {
          if (
            (event.relatedTarget as HTMLElement | null)?.closest(
              '[data-profile-save]',
            )
          )
            return;
          void save(draftRef.current);
        }}
      >
        <aside className="profile__sidebar">
          <Card className="profile__identity">
            <div className="profile__avatar">
              {profile?.avatar_url ? (
                <img
                  src={`${profile.avatar_url}?v=${encodeURIComponent(profile.updated_at)}`}
                  alt=""
                />
              ) : (
                <Icon name="user" />
              )}
            </div>
            <label className="ui-button profile__upload-button">
              <Icon name="image" />
              {avatarUploading ? 'Uploading…' : 'Change photo'}
              <input
                className="sr-only"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(event) => void uploadAvatar(event)}
                disabled={avatarUploading}
              />
            </label>
            {profile?.avatar_url && (
              <Button
                variant="danger"
                onClick={() =>
                  void profileApi
                    .removeAvatar()
                    .then((nextProfile) => {
                      setProfile(nextProfile);
                      announceProfileUpdate(nextProfile);
                      showToast('Profile photo removed.');
                    })
                    .catch((requestError) => {
                      showToast(
                        messageFor(requestError, 'Photo removal failed.'),
                        'error',
                      );
                    })
                }
              >
                Remove photo
              </Button>
            )}
            <FormField label="Name" htmlFor="profile-name">
              <Input
                id="profile-name"
                value={draft.full_name}
                onChange={(event) => update('full_name', event.target.value)}
              />
            </FormField>
            <FormField label="Professional headline" htmlFor="profile-headline">
              <Input
                id="profile-headline"
                value={draft.headline}
                onChange={(event) => update('headline', event.target.value)}
              />
            </FormField>
            <FormField label="Location" htmlFor="profile-location">
              <Input
                id="profile-location"
                value={draft.location}
                onChange={(event) => update('location', event.target.value)}
              />
            </FormField>
            <FormField label="LinkedIn URL" htmlFor="profile-linkedin">
              <Input
                id="profile-linkedin"
                type="url"
                value={
                  draft.links.find((link) => link.link_type === 'linkedin')
                    ?.url ?? ''
                }
                onChange={(event) => updateLink('linkedin', event.target.value)}
              />
            </FormField>
            <FormField label="Portfolio URL" htmlFor="profile-portfolio">
              <Input
                id="profile-portfolio"
                type="url"
                value={
                  draft.links.find((link) => link.link_type === 'portfolio')
                    ?.url ?? ''
                }
                onChange={(event) =>
                  updateLink('portfolio', event.target.value)
                }
              />
            </FormField>
          </Card>

          <Card>
            <h2>Core expertise</h2>
            <FormField
              label="Skills"
              htmlFor="profile-skills"
              hint="Separate skills with commas."
            >
              <Input
                id="profile-skills"
                value={draft.skills.join(', ')}
                onChange={(event) =>
                  update(
                    'skills',
                    event.target.value.split(',').map((value) => value.trim()),
                  )
                }
              />
            </FormField>
            <div className="profile__tags" aria-label="Current skills">
              {draft.skills.filter(Boolean).map((skill) => (
                <Badge key={skill}>{skill}</Badge>
              ))}
            </div>
          </Card>
        </aside>

        <div className="profile__content">
          <Card>
            <SectionHeading icon="report" title="Professional summary" />
            <textarea
              className="ui-input profile__textarea"
              aria-label="Professional summary"
              value={draft.summary}
              onChange={(event) => update('summary', event.target.value)}
              rows={7}
            />
            <div className="profile__contact-grid">
              <FormField label="Email" htmlFor="profile-email">
                <Input
                  id="profile-email"
                  type="email"
                  value={draft.email}
                  onChange={(event) => update('email', event.target.value)}
                />
              </FormField>
              <FormField label="Phone" htmlFor="profile-phone">
                <Input
                  id="profile-phone"
                  value={draft.phone}
                  onChange={(event) => update('phone', event.target.value)}
                />
              </FormField>
              <FormField label="Seniority" htmlFor="profile-seniority">
                <Input
                  id="profile-seniority"
                  value={draft.seniority}
                  onChange={(event) => update('seniority', event.target.value)}
                />
              </FormField>
              <FormField label="Availability" htmlFor="profile-availability">
                <Input
                  id="profile-availability"
                  value={draft.availability}
                  onChange={(event) =>
                    update('availability', event.target.value)
                  }
                />
              </FormField>
            </div>
          </Card>

          <CollectionSection
            title="Work experience"
            items={draft.experiences}
            onAdd={() =>
              update('experiences', [
                ...draft.experiences,
                {
                  id: newId(),
                  employer: '',
                  role: '',
                  start_date: null,
                  end_date: null,
                  is_current: false,
                  description: '',
                  position: draft.experiences.length,
                },
              ])
            }
            render={(item, index) => (
              <ExperienceEditor
                item={item}
                onChange={(next) =>
                  update(
                    'experiences',
                    replaceAt(draft.experiences, index, next),
                  )
                }
                onRemove={() =>
                  update(
                    'experiences',
                    draft.experiences.filter(
                      (_, itemIndex) => itemIndex !== index,
                    ),
                  )
                }
                onMoveUp={() =>
                  update('experiences', moveUp(draft.experiences, index))
                }
              />
            )}
          />

          <CollectionSection
            title="Projects"
            items={draft.projects}
            onAdd={() =>
              update('projects', [
                ...draft.projects,
                {
                  id: newId(),
                  name: '',
                  role: '',
                  description: '',
                  technologies: [],
                  url: null,
                  repository_url: null,
                  position: draft.projects.length,
                },
              ])
            }
            render={(item, index) => (
              <ProjectEditor
                item={item}
                onChange={(next) =>
                  update('projects', replaceAt(draft.projects, index, next))
                }
                onRemove={() =>
                  update(
                    'projects',
                    draft.projects.filter(
                      (_, itemIndex) => itemIndex !== index,
                    ),
                  )
                }
                onMoveUp={() =>
                  update('projects', moveUp(draft.projects, index))
                }
              />
            )}
          />
        </div>
      </div>

      <Dialog
        open={importOpen}
        onClose={() => {
          if (cvProcessing) return;
          setImportOpen(false);
          setSelectedCV(undefined);
        }}
        onCancel={(event) => {
          if (cvProcessing) event.preventDefault();
        }}
      >
        <div className="ui-dialog__content">
          <h2>{cvProcessing ? 'Processing your CV' : 'Import CV'}</h2>
          {cvProcessing ? (
            <div className="profile__processing">
              <Spinner label="Extracting profile information from CV" />
              <p>
                Extracting your profile, skills, and work experience with AI.
                This may take a moment.
              </p>
            </div>
          ) : (
            <>
              <label className="profile__dropzone">
                <Icon name="upload" />
                <strong>{selectedCV?.name ?? 'Choose a PDF CV'}</strong>
                <span>PDF up to 10 MB. The file is not stored.</span>
                <input
                  className="sr-only"
                  type="file"
                  accept="application/pdf,.pdf"
                  onChange={(event) => setSelectedCV(event.target.files?.[0])}
                />
              </label>
              <div className="ui-dialog__actions">
                <Button
                  onClick={() => {
                    setImportOpen(false);
                    setSelectedCV(undefined);
                  }}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  onClick={() => void importCV()}
                  disabled={!selectedCV}
                >
                  Import
                </Button>
              </div>
            </>
          )}
        </div>
      </Dialog>
    </>
  );
}

function SaveStatus({ status }: { status: SaveStatus }) {
  const labels = {
    idle: 'Profile loaded',
    pending: 'Unsaved changes',
    saving: 'Saving…',
    saved: 'All changes saved',
    error: 'Save failed',
  };
  return (
    <span className={`profile__save-status profile__save-status--${status}`}>
      {labels[status]}
    </span>
  );
}

function SectionHeading({
  icon,
  title,
}: {
  icon: Parameters<typeof Icon>[0]['name'];
  title: string;
}) {
  return (
    <div className="profile__section-heading">
      <Icon name={icon} />
      <h2>{title}</h2>
    </div>
  );
}

function CollectionSection<Item extends { id: string }>({
  title,
  items,
  onAdd,
  render,
}: {
  title: string;
  items: Item[];
  onAdd: () => void;
  render: (item: Item, index: number) => ReactNode;
}) {
  return (
    <Card>
      <div className="profile__collection-heading">
        <h2>{title}</h2>
        <Button onClick={onAdd}>
          <Icon name="plus" /> Add
        </Button>
      </div>
      {items.length === 0 ? (
        <p className="profile__empty">No {title.toLowerCase()} added yet.</p>
      ) : (
        <div className="profile__collection">
          {items.map((item, index) => (
            <Fragment key={item.id}>{render(item, index)}</Fragment>
          ))}
        </div>
      )}
    </Card>
  );
}

function ExperienceEditor({
  item,
  onChange,
  onRemove,
  onMoveUp,
}: {
  item: WorkExperience;
  onChange: (item: WorkExperience) => void;
  onRemove: () => void;
  onMoveUp: () => void;
}) {
  return (
    <fieldset className="profile__editor">
      <legend>{item.role || item.employer || 'New experience'}</legend>
      <div className="profile__editor-actions">
        <Button onClick={onMoveUp} aria-label="Move experience up">
          <Icon name="arrowUp" />
        </Button>
        <Button
          variant="danger"
          onClick={onRemove}
          aria-label="Remove experience"
        >
          <Icon name="trash" />
        </Button>
      </div>
      <Input
        aria-label="Employer"
        placeholder="Employer"
        value={item.employer}
        onChange={(event) =>
          onChange({ ...item, employer: event.target.value })
        }
      />
      <Input
        aria-label="Role"
        placeholder="Role"
        value={item.role}
        onChange={(event) => onChange({ ...item, role: event.target.value })}
      />
      <Input
        aria-label="Start date"
        type="date"
        value={item.start_date ?? ''}
        onChange={(event) =>
          onChange({ ...item, start_date: event.target.value || null })
        }
      />
      <Input
        aria-label="End date"
        type="date"
        value={item.end_date ?? ''}
        disabled={item.is_current}
        onChange={(event) =>
          onChange({ ...item, end_date: event.target.value || null })
        }
      />
      <label className="profile__checkbox">
        <input
          type="checkbox"
          checked={item.is_current}
          onChange={(event) =>
            onChange({
              ...item,
              is_current: event.target.checked,
              end_date: event.target.checked ? null : item.end_date,
            })
          }
        />
        Current role
      </label>
      <textarea
        className="ui-input profile__textarea profile__editor-description"
        aria-label="Experience description"
        placeholder="Responsibilities and achievements"
        value={item.description}
        onChange={(event) =>
          onChange({ ...item, description: event.target.value })
        }
      />
    </fieldset>
  );
}

function ProjectEditor({
  item,
  onChange,
  onRemove,
  onMoveUp,
}: {
  item: ProfileProject;
  onChange: (item: ProfileProject) => void;
  onRemove: () => void;
  onMoveUp: () => void;
}) {
  return (
    <fieldset className="profile__editor">
      <legend>{item.name || 'New project'}</legend>
      <div className="profile__editor-actions">
        <Button onClick={onMoveUp} aria-label="Move project up">
          <Icon name="arrowUp" />
        </Button>
        <Button variant="danger" onClick={onRemove} aria-label="Remove project">
          <Icon name="trash" />
        </Button>
      </div>
      <Input
        aria-label="Project name"
        placeholder="Project name"
        value={item.name}
        onChange={(event) => onChange({ ...item, name: event.target.value })}
      />
      <Input
        aria-label="Project role"
        placeholder="Your role"
        value={item.role}
        onChange={(event) => onChange({ ...item, role: event.target.value })}
      />
      <Input
        aria-label="Project technologies"
        placeholder="Technologies, comma separated"
        value={item.technologies.join(', ')}
        onChange={(event) =>
          onChange({
            ...item,
            technologies: event.target.value
              .split(',')
              .map((value) => value.trim()),
          })
        }
      />
      <Input
        aria-label="Project URL"
        type="url"
        placeholder="Project URL"
        value={item.url ?? ''}
        onChange={(event) =>
          onChange({ ...item, url: event.target.value || null })
        }
      />
      <Input
        aria-label="Repository URL"
        type="url"
        placeholder="Repository URL"
        value={item.repository_url ?? ''}
        onChange={(event) =>
          onChange({ ...item, repository_url: event.target.value || null })
        }
      />
      <textarea
        className="ui-input profile__textarea profile__editor-description"
        aria-label="Project description"
        placeholder="What you built and its impact"
        value={item.description}
        onChange={(event) =>
          onChange({ ...item, description: event.target.value })
        }
      />
    </fieldset>
  );
}

function replaceAt<Item>(items: Item[], index: number, item: Item): Item[] {
  const next = [...items];
  next[index] = item;
  return next;
}

function moveUp<Item>(items: Item[], index: number): Item[] {
  if (index === 0) return items;
  const next = [...items];
  [next[index - 1], next[index]] = [next[index], next[index - 1]];
  return next;
}

function messageFor(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.message : fallback;
}

export function ProfilePage() {
  return (
    <ToastProvider>
      <ProfileForm />
    </ToastProvider>
  );
}
