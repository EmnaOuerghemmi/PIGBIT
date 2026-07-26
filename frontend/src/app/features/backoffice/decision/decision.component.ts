import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  RecruitmentService, JobOffer, CandidateRanking,
} from '../../../core/services/recruitment.service';
import {
  ReportService, HiringRecommendation, EvaluateOfferResult,
} from '../../../core/services/report.service';

@Component({
  selector: 'app-decision',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './decision.component.html',
  styleUrls: ['./decision.component.css'],
})
export class DecisionComponent implements OnInit {
  // ── Recommandations d'embauche ─────────────────────────────────────────────
  jobs: JobOffer[] = [];
  selectedJobId = '';
  candidates: CandidateRanking[] = [];
  loadingCandidates = false;
  error = '';

  /** Recommandations chargées, indexées par application_id. */
  recommendations: Record<string, HiringRecommendation> = {};
  loadingRecId: string | null = null;

  // ── Évaluation d'offre salariale ───────────────────────────────────────────
  offerForm = { predicted_salary: null as number | null, offered_salary: null as number | null, confidence: 0.7 };
  offerResult: EvaluateOfferResult | null = null;
  evaluating = false;

  constructor(
    private recruitment: RecruitmentService,
    private reportService: ReportService,
  ) {}

  ngOnInit(): void {
    this.recruitment.getJobs(1, 100).subscribe({
      next: (res) => {
        this.jobs = res.items;
        if (!this.selectedJobId && this.jobs.length) {
          this.selectedJobId = this.jobs[0].id;
          this.loadCandidates();
        }
      },
    });
  }

  loadCandidates(): void {
    if (!this.selectedJobId) return;
    this.loadingCandidates = true;
    this.error = '';
    this.candidates = [];
    this.recommendations = {};
    this.recruitment.getRankedCandidates(this.selectedJobId).subscribe({
      next: (res) => {
        this.candidates = res.ranking;
        this.loadingCandidates = false;
      },
      error: (err) => {
        this.loadingCandidates = false;
        this.error = err?.error?.detail || 'Impossible de charger les candidats.';
      },
    });
  }

  getRecommendation(c: CandidateRanking): void {
    this.loadingRecId = c.application_id;
    this.reportService.getRecommendation(c.application_id).subscribe({
      next: (rec) => {
        this.recommendations[c.application_id] = rec;
        this.loadingRecId = null;
      },
      error: (err) => {
        this.loadingRecId = null;
        this.error = err?.error?.detail || 'Recommandation indisponible (candidat non analysé ?).';
      },
    });
  }

  recommendAll(): void {
    this.candidates.forEach((c) => {
      if (!this.recommendations[c.application_id]) this.getRecommendation(c);
    });
  }

  evaluateOffer(): void {
    const { predicted_salary, offered_salary, confidence } = this.offerForm;
    if (!predicted_salary || !offered_salary) return;
    this.evaluating = true;
    this.offerResult = null;
    this.reportService.evaluateOffer({ predicted_salary, offered_salary, confidence }).subscribe({
      next: (res) => { this.offerResult = res; this.evaluating = false; },
      error: (err) => {
        this.evaluating = false;
        this.error = err?.error?.detail || 'Évaluation impossible.';
      },
    });
  }

  // ── Helpers d'affichage ────────────────────────────────────────────────────

  recLabel(rec: string): string {
    return ({ HIRE: 'Recruter', INTERVIEW: 'Entretien', HOLD: 'En attente', REJECT: 'Rejeter' } as any)[rec] || rec;
  }
  recIcon(rec: string): string {
    return ({ HIRE: '✅', INTERVIEW: '🗓️', HOLD: '⏸️', REJECT: '❌' } as any)[rec] || '•';
  }
  decisionLabel(d: string): string {
    return ({ accept: 'Accepter', counter_offer: 'Contre-offre', reject: 'Rejeter' } as any)[d] || d;
  }
  decisionTone(d: string): string {
    return ({ accept: 'success', counter_offer: 'warn', reject: 'danger' } as any)[d] || 'info';
  }

  trackCandidate(_i: number, c: CandidateRanking): string { return c.application_id; }
}
