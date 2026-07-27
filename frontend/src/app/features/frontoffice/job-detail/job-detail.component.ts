import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Observable } from 'rxjs';
import { ActivatedRoute, Router } from '@angular/router';
import { RecruitmentService, JobOffer } from '../../../core/services/recruitment.service';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-job-detail',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './job-detail.component.html',
  styleUrls: ['./job-detail.component.css']
})
export class JobDetailComponent implements OnInit {
  job: JobOffer | null = null;
  isApplying = false;
  successMsg = '';
  errorMsg = '';
  selectedFile: File | null = null;
  analysisData: any = null;
  cvAnalysisData: any = null;
  currentApplicationId: string | null = null;
  isSaved = false;
  saving = false;

  get isAuthenticated(): boolean {
    return this.auth.isAuthenticated();
  }

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private recruitment: RecruitmentService,
    private auth: AuthService
  ) {}

  ngOnInit() {
    const jobId = this.route.snapshot.paramMap.get('id');
    if (jobId) {
      this.recruitment.getJob(jobId).subscribe({
        next: job => this.job = job,
        error: () => this.router.navigate(['/frontoffice/jobs'])
      });
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
      const allowedExt = ['.pdf', '.doc', '.docx'];
      const maxSize = 5 * 1024 * 1024;
      const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();

      // Some browsers report an empty MIME for .docx — fall back to extension.
      if (!allowedTypes.includes(file.type) && !allowedExt.includes(ext)) {
        this.errorMsg = 'Seuls les formats PDF, DOC et DOCX sont acceptés.';
        this.selectedFile = null;
        console.error('❌ File type not allowed:', file.type, ext);
        return;
      }

      if (file.size > maxSize) {
        this.errorMsg = 'La taille du fichier ne doit pas dépasser 5 MB';
        this.selectedFile = null;
        console.error('❌ File too large:', file.size);
        return;
      }

      this.selectedFile = file;
      this.errorMsg = '';
    } else {
    }
  }

  apply() {
    if (!this.job || !this.selectedFile) return;

    this.isApplying = true;
    this.errorMsg = '';
    this.successMsg = '';


    this.recruitment.applyToJob(this.job.id, this.selectedFile).subscribe({
      next: (application) => {
        this.isApplying = false;
        this.successMsg = 'Candidature envoyée avec succès ! Votre candidature est en cours de traitement.';
        this.selectedFile = null;
        this.currentApplicationId = application.id;

        setTimeout(() => {
          this.successMsg = '';
        }, 5000);
      },
      error: err => {
        console.error('❌ Application error:', err);
        this.isApplying = false;
        if (err?.status === 0) {
          this.errorMsg = 'Serveur injoignable. Vérifiez votre connexion et réessayez.';
        } else if (err?.status === 400) {
          this.errorMsg = err?.error?.detail || 'Fichier invalide (format ou taille).';
        } else if (err?.status === 401) {
          this.errorMsg = 'Session expirée. Reconnectez-vous pour postuler.';
        } else {
          this.errorMsg = err?.error?.detail || 'Erreur lors de la candidature. Réessayez.';
        }
      }
    });
  }

  toggleSave() {
    if (!this.job || this.saving) return;
    this.saving = true;
    const req: Observable<unknown> = this.isSaved
      ? this.recruitment.unsaveJob(this.job.id)
      : this.recruitment.saveJob(this.job.id);
    req.subscribe({
      next: () => { this.isSaved = !this.isSaved; this.saving = false; },
      error: (err: any) => { this.saving = false; this.errorMsg = err.error?.detail || 'Action impossible.'; },
    });
  }

  goBack() {
    this.router.navigate(['/frontoffice/jobs']);
  }

  goLogin() {
    this.router.navigate(['/login'], { queryParams: { returnUrl: this.router.url } });
  }

  getEducationLabel(level: string): string {
    const labels: Record<string, string> = {
      'HIGH_SCHOOL': 'Baccalauréat',
      'BACHELOR': 'Licence',
      'INGENIEUR': 'Ingénieur',
      'MASTER': 'Master',
      'PhD': 'Doctorat'
    };
    return labels[level] || level;
  }
}
