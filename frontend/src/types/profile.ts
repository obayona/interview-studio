export type ProfileLinkType = 'linkedin' | 'portfolio' | 'other';

export interface ProfileLink {
  id: string;
  link_type: ProfileLinkType;
  url: string;
  position: number;
}

export interface WorkExperience {
  id: string;
  employer: string;
  role: string;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
  description: string;
  position: number;
}

export interface ProfileProject {
  id: string;
  name: string;
  role: string;
  description: string;
  technologies: string[];
  url: string | null;
  repository_url: string | null;
  position: number;
}

export interface DeveloperProfile {
  id: string;
  full_name: string;
  headline: string;
  summary: string;
  location: string;
  email: string;
  phone: string;
  skills: string[];
  seniority: string;
  availability: string;
  links: ProfileLink[];
  experiences: WorkExperience[];
  projects: ProfileProject[];
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
}

export type ProfileDraft = Omit<
  DeveloperProfile,
  'id' | 'avatar_url' | 'created_at' | 'updated_at'
>;

export interface ProfileSuggestions {
  full_name: string | null;
  headline: string | null;
  summary: string | null;
  location: string | null;
  email: string | null;
  phone: string | null;
  skills: string[];
  experiences: WorkExperience[];
  projects: ProfileProject[];
}
