import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RecruitmentService, JobOffer, Application } from '../../../core/services/recruitment.service';
import { SafePipe } from '../../../core/pipes/safe.pipe';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { CandidateRankingComponent, WorkflowAction } from '../../../shared/components/candidate-ranking/candidate-ranking.component';
import { ScoreBreakdownComponent } from '../../../shared/components/score-breakdown/score-breakdown.component';
import { CVAnalysisComponent } from '../../../shared/components/cv-analysis/cv-analysis.component';
import { InterviewSchedulerComponent } from '../../../shared/components/interview-scheduler/interview-scheduler.component';
import { ToastService } from '../../../core/services/toast.service';
import { ConfirmService } from '../../../core/services/confirm.service';

@Component({
  selector: 'app-jobs-management',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    SafePipe,
    PaginationComponent,
    CandidateRankingComponent,
    ScoreBreakdownComponent,
    CVAnalysisComponent,
    InterviewSchedulerComponent,
  ],
  templateUrl: './jobs-management.component.html',
  styleUrls: ['./jobs-management.component.css']
})
export class JobsManagementComponent implements OnInit {
  private toast = inject(ToastService);
  private confirmService = inject(ConfirmService);

  jobs: JobOffer[] = [];
  filteredJobs: JobOffer[] = [];
  searchTerm = '';
  sortBy = '';
  drawerOpen = false;
  editingJob: JobOffer | null = null;
  formData = {
    title: '',
    description: '',
    salary_min: null as number | null,
    salary_max: null as number | null,
    required_skills: [] as string[],
    required_experience_years: null as number | null,
    required_education_level: '',
    weight_skills: 0.5,
    weight_experience: 0.3,
    weight_education: 0.2
  };
  skillsInput = '';
  applicantsModal = false;
  applicantsLoading = false;
  applicantsError = '';
  selectedJobId: string | null = null;
  selectedJobTitle = '';
  applicants: Application[] = [];
  paginatedApplicants: Application[] = [];
  applicantCurrentPage = 1;
  applicantPageSize = 10;
  applicantTotalPages = 1;
  applicantTab: 'list' | 'ranking' | 'analysis' = 'list';
  analysisFocusTab: 'score' | 'cv' = 'score';
  selectedApplicationId: string | null = null;
  cvPreviewOpen = false;
  cvPreviewPath = '';
  candidateCounts: Map<string, number> = new Map();

  // Workflow modals
  showInterviewModal = false;
  showNegotiationModal = false;
  workflowApplicationId: string | null = null;
  negotiationOffer: number | null = null;
  workflowLoading = false;
  workflowMessage = '';
  /** Increment to force the candidate-ranking component to refetch its data
   *  (so newly-scheduled interviews immediately disable the Planifier button). */
  rankingRefreshTrigger = 0;

  constructor(private recruitment: RecruitmentService) {}

  ngOnInit() {
    this.loadJobs();
  }

  loadJobs() {
    this.recruitment.getJobs(1, 100, this.searchTerm, this.sortBy).subscribe({
      next: res => {
        this.jobs = res.items;
        this.filteredJobs = res.items;
        this.loadCandidateCounts();
      }
    });
  }

  loadCandidateCounts() {
    this.jobs.forEach(job => {
      this.recruitment.getApplicationsByJob(job.id).subscribe({
        next: apps => this.candidateCounts.set(job.id, apps.length)
      });
    });
  }

  getCandidateCount(jobId: string): number {
    return this.candidateCounts.get(jobId) || 0;
  }

  applyFilters() {
    this.loadJobs();
  }

  openCreateDrawer() {
    this.editingJob = null;
    this.formData = {
      title: '',
      description: '',
      salary_min: null,
      salary_max: null,
      required_skills: [],
      required_experience_years: null,
      required_education_level: '',
      weight_skills: 0.5,
      weight_experience: 0.3,
      weight_education: 0.2
    };
    this.skillsInput = '';
    this.drawerOpen = true;
  }

  editJob(job: JobOffer) {
    this.editingJob = job;
    this.formData = {
      title: job.title,
      description: job.description,
      salary_min: job.salary_min,
      salary_max: job.salary_max,
      required_skills: job.required_skills || [],
      required_experience_years: job.required_experience_years ?? null,
      required_education_level: job.required_education_level || '',
      weight_skills: job.weight_skills || 0.5,
      weight_experience: job.weight_experience || 0.3,
      weight_education: job.weight_education || 0.2
    };
    this.skillsInput = (job.required_skills || []).join(', ');
    this.drawerOpen = true;
  }

  saveJob() {
    if (!this.formData.title || !this.formData.description) return;

    // Parse skills from the textarea input
    const skills = this.skillsInput
      .split(',')
      .map(s => s.trim())
      .filter(s => s.length > 0);

    const jobData = {
      ...this.formData,
      required_skills: skills
    };

    if (this.editingJob) {
      this.recruitment.updateJob(this.editingJob.id, jobData).subscribe({
        next: () => {
          this.closeDrawer();
          this.loadJobs();
        }
      });
    } else {
      this.recruitment.createJob(jobData).subscribe({
        next: () => {
          this.closeDrawer();
          this.loadJobs();
        }
      });
    }
  }

  closeDrawer() {
    this.drawerOpen = false;
    this.editingJob = null;
    this.formData = {
      title: '',
      description: '',
      salary_min: null,
      salary_max: null,
      required_skills: [],
      required_experience_years: null,
      required_education_level: '',
      weight_skills: 0.5,
      weight_experience: 0.3,
      weight_education: 0.2
    };
    this.skillsInput = '';
  }

  toggleJob(jobId: string, isActive: boolean) {
    this.recruitment.updateJob(jobId, { is_active: isActive }).subscribe({
      next: () => this.loadJobs()
    });
  }

  viewApplicants(jobId: string) {
    this.selectedJobId = jobId;
    const job = this.jobs.find(j => j.id === jobId);
    this.selectedJobTitle = job?.title || '';
    this.applicants = [];
    this.paginatedApplicants = [];
    this.applicantTab = 'list';
    this.applicantsError = '';
    this.applicantsLoading = true;
    this.applicantsModal = true;

    this.loadApplicants(jobId);
  }

  reloadApplicants() {
    if (this.selectedJobId) {
      this.applicantsError = '';
      this.applicantsLoading = true;
      this.loadApplicants(this.selectedJobId);
    }
  }

  private loadApplicants(jobId: string) {
    this.recruitment.getApplicationsByJob(jobId).subscribe({
      next: apps => {
        this.applicants = apps;
        this.applicantCurrentPage = 1;
        this.updateApplicantPagination();
        this.applicantsLoading = false;
      },
      error: error => {
        this.applicants = [];
        this.paginatedApplicants = [];
        this.applicantsLoading = false;
        if (error.status === 401) {
          this.applicantsError = 'Votre session a expiré. Reconnectez-vous puis réessayez.';
        } else if (error.status === 403) {
          this.applicantsError = 'Vous n’avez pas les permissions nécessaires pour consulter ces candidatures.';
        } else {
          this.applicantsError = error.error?.detail || 'Une erreur est survenue pendant le chargement.';
        }
      }
    });
  }

  updateApplicantPagination() {
    this.applicantTotalPages = Math.ceil(this.applicants.length / this.applicantPageSize);
    const start = (this.applicantCurrentPage - 1) * this.applicantPageSize;
    const end = start + this.applicantPageSize;
    this.paginatedApplicants = this.applicants.slice(start, end);
  }

  goToApplicantPage(page: number) {
    this.applicantCurrentPage = page;
    this.updateApplicantPagination();
  }

  onApplicantPageSizeChange(newSize: number) {
    this.applicantPageSize = newSize;
    this.applicantCurrentPage = 1;
    this.updateApplicantPagination();
  }

  closeApplicants() {
    this.applicantsModal = false;
    this.applicantsLoading = false;
    this.applicantsError = '';
    this.applicants = [];
    this.paginatedApplicants = [];
  }

  previewCV(cvPath: string) {
    this.recruitment.downloadCVAsBlob(cvPath).subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        this.cvPreviewPath = url;
        this.cvPreviewOpen = true;
      },
      error: err => this.toast.fromHttpError(err, 'Impossible de charger le CV.')
    });
  }

  closeCVPreview() {
    this.cvPreviewOpen = false;
    if (this.cvPreviewPath.startsWith('blob:')) {
      URL.revokeObjectURL(this.cvPreviewPath);
    }
    this.cvPreviewPath = '';
  }

  viewAnalysis(applicationId: string) {
    this.selectedApplicationId = applicationId;
    this.applicantTab = 'analysis';
    this.analysisFocusTab = 'score';
  }

  getInitials(name: string): string {
    return name
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map(part => part[0])
      .join('')
      .toUpperCase();
  }

  downloadCV(cvPath: string) {
    this.recruitment.downloadCVAsBlob(cvPath).subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = cvPath.split('/').pop() || 'cv.pdf';
        link.click();
        URL.revokeObjectURL(url);
      },
      error: err => this.toast.fromHttpError(err, 'Le téléchargement du CV a échoué.')
    });
  }

  updateAppStatus(appId: string, event: Event) {
    const status = (event.target as HTMLSelectElement).value;
    this.recruitment.updateApplication(appId, status).subscribe({
      next: () => {
        if (this.selectedJobId) {
          this.recruitment.getApplicationsByJob(this.selectedJobId).subscribe({
            next: apps => {
              this.applicants = apps;
              this.updateApplicantPagination();
            }
          });
        }
      }
    });
  }

  // ── Workflow handlers ──────────────────────────────────────────

  onScheduleInterview(action: WorkflowAction) {
    this.workflowApplicationId = action.applicationId;
    this.showInterviewModal = true;
  }

  onInterviewSchedulerClosed(success: boolean) {
    this.showInterviewModal = false;
    this.workflowApplicationId = null;
    if (success) {
      this.workflowMessage = 'Entretien planifié avec succès. Email envoyé au candidat.';
      // Force the candidate-ranking to refresh so the Planifier button
      // immediately disables for this candidate.
      this.rankingRefreshTrigger++;
    }
  }

  onStartNegotiation(action: WorkflowAction) {
    this.workflowApplicationId = action.applicationId;
    this.negotiationOffer = null;
    this.showNegotiationModal = true;
  }

  confirmNegotiation() {
    if (!this.workflowApplicationId || !this.negotiationOffer) return;
    this.workflowLoading = true;
    this.recruitment.startNegotiation(this.workflowApplicationId, this.negotiationOffer).subscribe({
      next: (res: any) => {
        this.workflowLoading = false;
        this.showNegotiationModal = false;
        this.workflowApplicationId = null;
        if (res?.negotiation_status) {
          const statusFr: Record<string, string> = {
            ACCEPTED: 'Accord trouvé ✅', REJECTED: 'Offre rejetée ❌', COMPROMIS: 'Compromis 🤝',
          };
          this.workflowMessage =
            `${statusFr[res.negotiation_status] || res.negotiation_status} — ` +
            `salaire prédit ${res.predicted_salary} TND, offre finale ${res.final_salary} TND ` +
            `(${res.rounds || 0} tour(s)). ${res.reason || ''}`;
        } else {
          this.workflowMessage = res?.message || 'Négociation lancée.';
        }
      },
      error: () => {
        this.workflowLoading = false;
        this.workflowMessage = 'Erreur lors du lancement de la négociation.';
      }
    });
  }

  async onRejectCandidate(action: WorkflowAction) {
    const ok = await this.confirmService.ask({
      title: 'Rejeter la candidature',
      message: `Rejeter cette candidature (score ${action.score.toFixed(0)}/100) ? Un email de refus sera envoyé au candidat.`,
      confirmLabel: 'Rejeter',
      danger: true,
    });
    if (!ok) return;
    this.recruitment.rejectApplication(action.applicationId).subscribe({
      next: () => {
        this.workflowMessage = 'Candidature rejetée. Email envoyé au candidat.';
      },
      error: () => {
        this.workflowMessage = 'Erreur lors du rejet de la candidature.';
      }
    });
  }

  closeWorkflowMessage() {
    this.workflowMessage = '';
  }
}
