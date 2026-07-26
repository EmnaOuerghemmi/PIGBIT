import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { environment } from '../../../environments/environment';

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

export interface ReportContent {
  narrative: string;
  highlights: string[];
  recommendations: string[];
  generated_by: 'deterministic' | 'claude';
}

export interface ReportSnapshot {
  id: string;
  report_type: string;
  title: string | null;
  data: Partial<RecruitmentSummary> & { report?: ReportContent };
  created_at: string;
}

export interface PaginatedReports {
  items: ReportSnapshot[];
  total: number;
  page: number;
  pages: number;
  page_size: number;
}

export interface EvaluateOfferResult {
  decision: string;
  reason: string;
  counter_offer: number | null;
}

export interface HiringRecommendation {
  application_id: string;
  total_score: number;
  recommendation: 'HIRE' | 'INTERVIEW' | 'HOLD' | 'REJECT';
  confidence: 'high' | 'medium' | 'low';
  rationale: string;
}

@Injectable({ providedIn: 'root' })
export class ReportService {
  constructor(private api: ApiService) {}

  // ── Analytics live ────────────────────────────────────────────────────────

  getSummary(): Observable<RecruitmentSummary> {
    return this.api.get<RecruitmentSummary>('reports/recruitment-summary');
  }

  // ── CRUD des rapports archivés ────────────────────────────────────────────

  listReports(page = 1, pageSize = 10): Observable<PaginatedReports> {
    return this.api.get<PaginatedReports>('reports', { page, page_size: pageSize });
  }

  getReport(id: string): Observable<ReportSnapshot> {
    return this.api.get<ReportSnapshot>(`reports/${id}`);
  }

  /** Génère un rapport via l'agent de reporting et l'archive. */
  generateReport(title?: string): Observable<ReportSnapshot> {
    return this.api.post<ReportSnapshot>('reports/snapshot', title ? { title } : {});
  }

  renameReport(id: string, title: string): Observable<ReportSnapshot> {
    return this.api.patch<ReportSnapshot>(`reports/${id}`, { title });
  }

  deleteReport(id: string): Observable<void> {
    return this.api.delete<void>(`reports/${id}`);
  }

  /** Télécharge le PDF du rapport (blob). */
  downloadPdf(id: string): Observable<Blob> {
    return this.api.http.get(`${environment.apiUrl}/reports/${id}/pdf`, {
      responseType: 'blob',
    });
  }

  // ── Décision ──────────────────────────────────────────────────────────────

  evaluateOffer(payload: {
    predicted_salary: number; offered_salary: number; confidence?: number;
  }): Observable<EvaluateOfferResult> {
    return this.api.post<EvaluateOfferResult>('decision/evaluate-offer', payload);
  }

  getRecommendation(applicationId: string): Observable<HiringRecommendation> {
    return this.api.get<HiringRecommendation>(`decision/applications/${applicationId}/recommendation`);
  }
}
