import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import {
  RecruitmentService, JobOffer, RecruitmentSummary,
} from '../../../core/services/recruitment.service';
import { ConfirmService } from '../../../core/services/confirm.service';
import {
  SemanticService, SemanticStatus, SemanticMatch,
} from '../../../core/services/semantic.service';
import {
  CandidateRankingComponent, WorkflowAction,
} from '../../../shared/components/candidate-ranking/candidate-ranking.component';

@Component({
  selector: 'app-recruitment',
  standalone: true,
  imports: [CommonModule, FormsModule, CandidateRankingComponent],
  templateUrl: './recruitment.component.html',
  styleUrls: ['./recruitment.component.css'],
})
export class RecruitmentComponent implements OnInit {
  private confirmService = inject(ConfirmService);

  summary: RecruitmentSummary | null = null;
  jobs: JobOffer[] = [];
  selectedJobId = '';
  analyzing = false;
  message = '';
  messageTone: 'info' | 'success' | 'error' = 'info';
  rankingRefresh = 0;
  candidateCounts = new Map<string, number>();
  jobSearch = '';

  // ── Matching sémantique ──
  semanticStatus: SemanticStatus | null = null;
  semanticResults: SemanticMatch[] = [];
  semanticLoading = false;
  semanticRan = false;

  // ── Candidats similaires (panneau) ──
  similarFor: SemanticMatch | null = null;
  similarResults: SemanticMatch[] = [];
  similarLoading = false;

  constructor(
    private recruitment: RecruitmentService,
    private semantic: SemanticService,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.loadSummary();
    this.loadJobs();
    this.semantic.getStatus().subscribe({
      next: s => this.semanticStatus = s,
      error: () => {},
    });
  }

  // ════════════ Matching sémantique ════════════

  runSemanticMatch(): void {
    if (!this.selectedJobId) return;
    this.semanticLoading = true;
    this.semanticRan = true;
    this.semanticResults = [];
    this.closeSimilar();
    this.semantic.matchCandidates(this.selectedJobId, 10).subscribe({
      next: res => {
        this.semanticResults = res.results;
        this.semanticLoading = false;
      },
      error: err => {
        this.semanticLoading = false;
        this.messageTone = 'error';
        this.message = err?.error?.detail || 'Matching sémantique indisponible.';
      },
    });
  }

  showSimilar(match: SemanticMatch): void {
    this.similarFor = match;
    this.similarResults = [];
    this.similarLoading = true;
    this.semantic.similarCandidates(match.application_id, 5).subscribe({
      next: res => { this.similarResults = res.results; this.similarLoading = false; },
      error: () => { this.similarLoading = false; },
    });
  }

  closeSimilar(): void {
    this.similarFor = null;
    this.similarResults = [];
  }

  semanticBackendLabel(): string {
    if (!this.semanticStatus) return '';
    return this.semanticStatus.effective_backend === 'hash-v1'
      ? 'mode lexical (fallback)' : 'modèle neuronal';
  }

  semanticTone(score: number): string {
    if (score >= 70) return 'success';
    if (score >= 40) return 'warn';
    return 'muted';
  }

  trackMatch(_i: number, m: SemanticMatch): string { return m.application_id; }

  loadSummary(): void {
    this.recruitment.getRecruitmentSummary().subscribe({
      next: s => this.summary = s,
      error: () => {},
    });
  }

  loadJobs(): void {
    this.recruitment.getJobs(1, 100).subscribe({
      next: res => {
        this.jobs = res.items;
        if (!this.selectedJobId && this.jobs.length) {
          this.selectedJobId = this.jobs[0].id;
        }
        this.jobs.forEach(j => {
          this.recruitment.getApplicationsByJob(j.id).subscribe({
            next: apps => this.candidateCounts.set(j.id, apps.length),
            error: () => {},
          });
        });
      },
    });
  }

  get filteredJobs(): JobOffer[] {
    const q = this.jobSearch.trim().toLowerCase();
    if (!q) return this.jobs;
    return this.jobs.filter(j => j.title.toLowerCase().includes(q));
  }

  get selectedJob(): JobOffer | undefined {
    return this.jobs.find(j => j.id === this.selectedJobId);
  }

  count(jobId: string): number {
    return this.candidateCounts.get(jobId) || 0;
  }

  selectJob(id: string): void {
    this.selectedJobId = id;
    this.message = '';
    this.semanticResults = [];
    this.semanticRan = false;
    this.closeSimilar();
  }

  eduLabel(level: string | null | undefined): string {
    const m: Record<string, string> = {
      HIGH_SCHOOL: 'Bac', BACHELOR: 'Licence', INGENIEUR: 'Ingénieur', MASTER: 'Master', PHD: 'Doctorat',
    };
    return level ? (m[level] || level) : '—';
  }

  analyzeAll(): void {
    if (!this.selectedJobId) return;
    this.analyzing = true;
    this.message = '';
    this.recruitment.analyzeAllForJob(this.selectedJobId).subscribe({
      next: () => {
        this.analyzing = false;
        this.messageTone = 'info';
        this.message = 'Analyse IA lancée. Le classement se met à jour dans quelques instants…';
        setTimeout(() => this.rankingRefresh++, 2500);
      },
      error: err => {
        this.analyzing = false;
        this.messageTone = 'error';
        this.message = err.error?.detail || 'Erreur lors du lancement de l’analyse.';
      },
    });
  }

  async onReject(a: WorkflowAction): Promise<void> {
    const ok = await this.confirmService.ask({
      title: 'Rejeter le candidat',
      message: `Rejeter ce candidat (score ${a.score.toFixed(0)}/100) ? Un email de refus lui sera envoyé.`,
      confirmLabel: 'Rejeter',
      danger: true,
    });
    if (!ok) return;
    this.recruitment.rejectApplication(a.applicationId).subscribe({
      next: () => { this.messageTone = 'success'; this.message = 'Candidature rejetée. Email envoyé.'; this.rankingRefresh++; },
      error: () => { this.messageTone = 'error'; this.message = 'Erreur lors du rejet.'; },
    });
  }

  onStartNegotiation(a: WorkflowAction): void {
    const offer = Number(window.prompt('Offre salariale initiale (k TND) :', '50'));
    if (!offer || offer <= 0) return;
    this.recruitment.startNegotiation(a.applicationId, offer).subscribe({
      next: (res: any) => {
        this.messageTone = 'success';
        if (res?.negotiation_status) {
          const statusFr: Record<string, string> = {
            ACCEPTED: 'Accord trouvé ✅', REJECTED: 'Offre rejetée ❌', COMPROMIS: 'Compromis 🤝',
          };
          this.message =
            `${statusFr[res.negotiation_status] || res.negotiation_status} — ` +
            `salaire prédit ${res.predicted_salary} TND, offre finale ${res.final_salary} TND ` +
            `(${res.rounds || 0} tour(s)).`;
        } else {
          this.message = res?.message || 'Négociation lancée.';
        }
      },
      error: () => { this.messageTone = 'error'; this.message = 'Erreur lors du lancement de la négociation.'; },
    });
  }

  onScheduleInterview(_a: WorkflowAction): void {
    this.messageTone = 'info';
    this.message = 'Planification d’entretien : utilisez la page « Offres » → « Voir candidats ».';
    this.router.navigate(['/admin/jobs']);
  }
}
