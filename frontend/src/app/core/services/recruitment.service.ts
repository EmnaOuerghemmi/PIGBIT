import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { environment } from '../../../environments/environment';

export interface JobOffer {
  id: string;
  title: string;
  description: string;
  salary_min: number | null;
  salary_max: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  required_skills?: string[];
  required_experience_years?: number;
  required_education_level?: string;
  weight_skills?: number;
  weight_experience?: number;
  weight_education?: number;
}

export interface Application {
  id: string;
  candidate_id: string;
  candidate_name?: string;
  job_offer_id: string;
  job_offer_title?: string;
  cv_file_path: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface MyApplication {
  id: string;
  job_offer_id: string;
  candidate_id: string;
  cv_file_path: string;
  status: string;
  created_at: string;
  updated_at: string;
  job_title: string;
  job_description: string;
  job_salary_min: number | null;
  job_salary_max: number | null;
  job_required_skills: string[] | null;
  job_required_experience_years: number | null;
  job_required_education_level: string | null;
  job_is_active: boolean;
  total_score: number | null;
  skills_score: number | null;
  experience_score: number | null;
  education_score: number | null;
}

export interface JobOfferWithCandidateCount extends JobOffer {
  candidate_count: number;
}

export interface PaginatedJobs {
  total: number;
  page: number;
  size: number;
  items: JobOffer[];
}

export interface CandidateRanking {
  candidate_id: string;
  candidate_name?: string;
  application_id: string;
  total_score: number;
  rank: number | null;
  skills_score: number;
  experience_score: number;
  education_score: number;
  score_details: ScoreDetails | null;
  // Set when the backend finds an active interview invitation for this app.
  interview_status?: 'PENDING' | 'CONFIRMED' | null;
  interview_invitation_id?: string | null;
  interview_confirmed_at?: string | null;
}

export interface RankingResponse {
  job_offer_id: string;
  total_candidates: number;
  ranking: CandidateRanking[];
}

export interface ScoreDetails {
  matched_skills: string[];
  missing_skills: string[];
  required_skills: string[];
  extracted_years: number | null;
  required_years: number | null;
  extracted_education: string | null;
  required_education: string | null;
  weights: { skills: number; experience: number; education: number };
  strengths: string[];
  weaknesses: string[];
  recommendation: string;
}

export interface CandidateScoreResponse {
  id: string;
  application_id: string;
  job_offer_id: string;
  candidate_id: string;
  total_score: number;
  skills_score: number;
  experience_score: number;
  education_score: number;
  rank: number | null;
  score_details: ScoreDetails | null;
  computed_at: string;
}

export interface CVAnalysisResponse {
  id: string;
  application_id: string;
  candidate_id: string;
  extracted_skills: string[];
  extracted_experience_years: number | null;
  extracted_education_level: string;
  extracted_job_titles: string[];
  extracted_keywords: string[];
  is_parsed: boolean;
  parsed_at: string | null;
  created_at: string;
}

export interface AnalysisStartedResponse {
  message: string;
  application_id: string | null;
  job_id: string | null;
}

export interface LabelCount { label: string; count: number; }
export interface ApplicationsTimeline {
  series: { date: string; label: string; count: number }[];
  total: number;
}
export interface CandidateAnalytics {
  experience_buckets: LabelCount[];
  score_bands: LabelCount[];
  education: LabelCount[];
  top_skills: LabelCount[];
  analyzed_cvs: number;
  scored_candidates: number;
  generated_at: string;
}

export interface RecruitmentSummary {
  total_jobs: number;
  active_jobs: number;
  total_applications: number;
  applications_by_status: Record<string, number>;
  acceptance_rate: number;
  average_score: number | null;
  top_jobs: { job_offer_id: string; title: string; application_count: number }[];
  generated_at: string;
}

// ─── Interview workflow ───
export type InvitationStatus = 'PENDING' | 'CONFIRMED' | 'EXPIRED' | 'CANCELLED';
export type SlotState = 'AVAILABLE' | 'PROPOSED' | 'RESERVED';

export interface InterviewSlot {
  id: string;
  invitation_id: string;
  start_at: string;
  end_at: string;
  is_selected: boolean;
}

export interface InvitationResponse {
  id: string;
  application_id: string;
  token: string;
  status: InvitationStatus;
  message: string | null;
  expires_at: string;
  confirmed_slot_id: string | null;
  confirmed_at: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  created_at: string;
  updated_at: string;
  slots: InterviewSlot[];
  candidate_name: string | null;
  candidate_email: string | null;
  job_title: string | null;
  public_url: string;
}

export interface PublicInvitationView {
  status: InvitationStatus;
  expires_at: string;
  message: string | null;
  candidate_name: string;
  job_title: string;
  job_description: string | null;
  company_name: string;
  slots: InterviewSlot[];
  confirmed_slot: InterviewSlot | null;
}

export interface CalendarSlot {
  id: string;
  invitation_id: string;
  application_id: string;
  start_at: string;
  end_at: string;
  state: SlotState;
  candidate_name: string | null;
  job_title: string | null;
  invitation_status: InvitationStatus;
  confirmed_at: string | null;
}

export interface CalendarResponse {
  total: number;
  items: CalendarSlot[];
}

@Injectable({ providedIn: 'root' })
export class RecruitmentService {
  constructor(private api: ApiService) {}

  getJobs(page = 1, size = 10, search?: string, sortBy?: string): Observable<PaginatedJobs> {
    const params: Record<string, string | number> = { page, size };
    if (search) params['search'] = search;
    if (sortBy) params['sort_by'] = sortBy;
    return this.api.get<PaginatedJobs>('recruitment/jobs', params);
  }

  getJob(jobId: string): Observable<JobOffer> {
    return this.api.get<JobOffer>(`recruitment/jobs/${jobId}`);
  }

  createJob(data: any): Observable<JobOffer> {
    return this.api.post<JobOffer>('recruitment/jobs', data);
  }

  updateJob(jobId: string, data: any): Observable<JobOffer> {
    return this.api.patch<JobOffer>(`recruitment/jobs/${jobId}`, data);
  }

  deleteJob(jobId: string): Observable<void> {
    return this.api.delete<void>(`recruitment/jobs/${jobId}`);
  }

  applyToJob(jobId: string, cvFile: File): Observable<Application> {
    const formData = new FormData();
    formData.append('cv_file', cvFile);
    return this.api.postFormData<Application>(`recruitment/apply/${jobId}`, formData);
  }

  getApplications(jobId?: string, page = 1, size = 20): Observable<Application[]> {
    const params: Record<string, string | number> = { page, size };
    if (jobId) params['job_id'] = jobId;
    return this.api.get<Application[]>('recruitment/applications', params);
  }

  /** Authenticated user's own applications, enriched with job offer details + score. */
  getMyApplications(): Observable<MyApplication[]> {
    return this.api.get<MyApplication[]>('recruitment/my-applications');
  }

  getApplicationsByJob(jobId: string): Observable<Application[]> {
    return this.api.get<Application[]>(`recruitment/jobs/${jobId}/applications`);
  }

  updateApplication(appId: string, status: string): Observable<Application> {
    return this.api.patch<Application>(`recruitment/applications/${appId}`, { status });
  }

  /** CAND-08 — hard-delete an application (Admin only). */
  deleteApplication(appId: string): Observable<void> {
    return this.api.delete<void>(`recruitment/applications/${appId}`);
  }

  /** Full update of a job offer (PUT). */
  replaceJob(jobId: string, data: any): Observable<JobOffer> {
    return this.api.put<JobOffer>(`recruitment/jobs/${jobId}`, data);
  }

  // ─── Saved jobs (frontoffice bookmarks) ───
  getSavedJobs(): Observable<JobOffer[]> {
    return this.api.get<JobOffer[]>('recruitment/saved-jobs');
  }

  saveJob(jobId: string): Observable<JobOffer> {
    return this.api.post<JobOffer>(`recruitment/saved-jobs/${jobId}`, {});
  }

  unsaveJob(jobId: string): Observable<void> {
    return this.api.delete<void>(`recruitment/saved-jobs/${jobId}`);
  }

  /** Export applications as a CSV blob (optionally filtered by job). */
  exportApplications(jobId?: string): Observable<Blob> {
    const qs = jobId ? `?job_id=${jobId}` : '';
    return this.api.http.get(
      `${environment.apiUrl}/recruitment/applications/export${qs}`,
      { responseType: 'blob' },
    );
  }

  getCVDownloadUrl(cvPath: string): string {
    const encodedPath = encodeURIComponent(cvPath);
    return `http://localhost:8000/api/v1/recruitment/cv-download/${encodedPath}`;
  }

  getCVPreviewUrl(cvPath: string): string {
    const encodedPath = encodeURIComponent(cvPath);
    return `http://localhost:8000/api/v1/recruitment/cv-preview/${encodedPath}`;
  }

  downloadCVAsBlob(cvPath: string): Observable<Blob> {
    const encodedPath = encodeURIComponent(cvPath);
    return this.api.http.get(`http://localhost:8000/api/v1/recruitment/cv-preview/${encodedPath}`,
      { responseType: 'blob' });
  }

  analyzeApplication(appId: string): Observable<AnalysisStartedResponse> {
    return this.api.post<AnalysisStartedResponse>(`recruitment/applications/${appId}/analyze`, {});
  }

  /** Trigger CV analysis + scoring for all applications of a job. */
  analyzeAllForJob(jobId: string): Observable<AnalysisStartedResponse> {
    return this.api.post<AnalysisStartedResponse>(`recruitment/jobs/${jobId}/analyze-all`, {});
  }

  /** Live recruitment KPIs (reports module). */
  getRecruitmentSummary(): Observable<RecruitmentSummary> {
    return this.api.get<RecruitmentSummary>('reports/recruitment-summary');
  }

  /** Candidate distributions (experience, AI score band, education, top skills). */
  getCandidateAnalytics(): Observable<CandidateAnalytics> {
    return this.api.get<CandidateAnalytics>('reports/candidate-analytics');
  }

  /** Daily applications over the last N days (evolution chart). */
  getApplicationsTimeline(days = 14): Observable<ApplicationsTimeline> {
    return this.api.get<ApplicationsTimeline>('reports/applications-timeline', { days });
  }

  scheduleInterview(
    appId: string,
    slots: string[],
    message: string,
    durationMinutes = 30,
    expiresInHours = 48,
  ): Observable<{ message: string }> {
    return this.api.post(`recruitment/applications/${appId}/schedule-interview`, {
      slots,
      message,
      duration_minutes: durationMinutes,
      expires_in_hours: expiresInHours,
    });
  }

  // ─── Public (no auth) — invitation confirm page ───
  getPublicInvitation(token: string): Observable<PublicInvitationView> {
    return this.api.get<PublicInvitationView>(`interview/confirm/${token}`);
  }

  confirmInvitationSlot(token: string, slotId: string): Observable<PublicInvitationView> {
    return this.api.post<PublicInvitationView>(`interview/confirm/${token}`, { slot_id: slotId });
  }

  /** Lightweight check: does this application already have a PENDING/CONFIRMED invitation? */
  getActiveInvitationForApplication(appId: string): Observable<{
    active: boolean;
    id?: string;
    status?: InvitationStatus;
    token?: string;
    expires_at?: string;
    confirmed_slot_id?: string | null;
    confirmed_at?: string | null;
    public_url?: string;
  }> {
    return this.api.get(`interview/applications/${appId}/active-invitation`);
  }

  // ─── RH ───
  listInvitations(filter?: { status?: InvitationStatus; applicationId?: string }): Observable<InvitationResponse[]> {
    const params: Record<string, string | number> = {};
    if (filter?.status)        params['status']         = filter.status;
    if (filter?.applicationId) params['application_id'] = filter.applicationId;
    return this.api.get<InvitationResponse[]>('interview/invitations', params);
  }

  getInvitation(invitationId: string): Observable<InvitationResponse> {
    return this.api.get<InvitationResponse>(`interview/invitations/${invitationId}`);
  }

  cancelInvitation(invitationId: string, reason: string = ''): Observable<InvitationResponse> {
    return this.api.post<InvitationResponse>(`interview/invitations/${invitationId}/cancel`, { reason });
  }

  getInterviewCalendar(filter?: { dateFrom?: string; dateTo?: string; state?: SlotState }): Observable<CalendarResponse> {
    const params: Record<string, string> = {};
    if (filter?.dateFrom) params['date_from'] = filter.dateFrom;
    if (filter?.dateTo)   params['date_to']   = filter.dateTo;
    if (filter?.state)    params['state']     = filter.state;
    return this.api.get<CalendarResponse>('interview/calendar', params);
  }

  /** État de l'intégration Google Calendar côté serveur. */
  getGoogleCalendarStatus(): Observable<{ configured: boolean; calendar_id: string | null; reason: string | null }> {
    return this.api.get('interview/google-status');
  }

  /** (Re)pousse un entretien confirmé vers Google Calendar. */
  syncInvitationToGoogle(invitationId: string): Observable<{ synced: boolean; google_event_id: string; already: boolean }> {
    return this.api.post(`interview/invitations/${invitationId}/sync-google`, {});
  }

  /** Télécharge le fichier .ics (RFC 5545) d'un entretien confirmé. */
  downloadInvitationIcs(invitationId: string): Observable<Blob> {
    return this.api.http.get(`${environment.apiUrl}/interview/invitations/${invitationId}/ics`, {
      responseType: 'blob',
    });
  }

  rejectApplication(appId: string, message: string = ''): Observable<{ message: string }> {
    return this.api.post(`recruitment/applications/${appId}/reject`, { message });
  }

  startNegotiation(appId: string, employerOffer: number): Observable<any> {
    return this.api.post(`recruitment/applications/${appId}/start-negotiation`, { employer_offer: employerOffer });
  }

  getRankedCandidates(jobId: string): Observable<RankingResponse> {
    return this.api.get<RankingResponse>(`recruitment/jobs/${jobId}/ranking`);
  }

  getScoreBreakdown(appId: string): Observable<CandidateScoreResponse> {
    return this.api.get<CandidateScoreResponse>(`recruitment/applications/${appId}/score`);
  }

  getExtractedCVData(appId: string): Observable<CVAnalysisResponse> {
    return this.api.get<CVAnalysisResponse>(`recruitment/applications/${appId}/analysis`);
  }
}
