import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { RecruitmentService, Application } from '../../../core/services/recruitment.service';
import { ContractService } from '../../../core/services/contract.service';
import { SafePipe } from '../../../core/pipes/safe.pipe';

@Component({
  selector: 'app-applications',
  standalone: true,
  imports: [CommonModule, SafePipe],
  templateUrl: './applications.component.html',
  styleUrls: ['./applications.component.css']
})
export class ApplicationsComponent implements OnInit {
  applications: Application[] = [];
  cvPreviewOpen = false;
  cvPreviewPath = '';
  generatingContract: string | null = null;

  constructor(
    private recruitment: RecruitmentService,
    private contracts: ContractService,
    private router: Router,
  ) {}

  /** Un candidat accepté/en négociation peut recevoir un contrat. */
  getInitials(name: string): string {
    return name
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map(part => part[0])
      .join('')
      .toUpperCase();
  }

  canGenerateContract(app: Application): boolean {
    return app.status === 'ACCEPTED' || app.status === 'NEGOTIATION';
  }

  generateContract(app: Application) {
    this.generatingContract = app.id;
    this.contracts.createFromApplication(app.id, { contract_type: 'CDI' }).subscribe({
      next: () => {
        this.generatingContract = null;
        this.router.navigate(['/admin/contracts']);
      },
      error: (err) => {
        this.generatingContract = null;
        alert(err?.error?.detail || 'Impossible de générer le contrat.');
        if (err?.status === 409) this.router.navigate(['/admin/contracts']);
      },
    });
  }

  ngOnInit() {
    this.loadApplications();
  }

  loadApplications() {
    this.recruitment.getApplications().subscribe({
      next: res => this.applications = res
    });
  }

  updateStatus(appId: string, event: Event) {
    const status = (event.target as HTMLSelectElement).value;
    this.recruitment.updateApplication(appId, status).subscribe({
      next: () => this.loadApplications()
    });
  }

  deleteApp(appId: string) {
    if (confirm('Supprimer définitivement cette candidature et son CV ? Cette action est irréversible.')) {
      this.recruitment.deleteApplication(appId).subscribe({
        next: () => this.loadApplications(),
        error: err => alert('Erreur: ' + (err.error?.detail || 'Suppression impossible (réservée aux administrateurs).'))
      });
    }
  }

  exportCsv() {
    this.recruitment.exportApplications().subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'candidatures.csv';
        link.click();
        URL.revokeObjectURL(url);
      },
      error: err => alert('Erreur export: ' + (err.error?.detail || 'Export impossible'))
    });
  }

  getCVDownloadUrl(cvPath: string): string {
    return this.recruitment.getCVDownloadUrl(cvPath);
  }

  openCVPreview(cvPath: string) {
    this.recruitment.downloadCVAsBlob(cvPath).subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        this.cvPreviewPath = url;
        this.cvPreviewOpen = true;
      },
      error: err => alert('Erreur: ' + (err.error?.detail || 'Impossible de charger le CV'))
    });
  }

  closeCVPreview() {
    if (this.cvPreviewPath.startsWith('blob:')) {
      URL.revokeObjectURL(this.cvPreviewPath);
    }
    this.cvPreviewOpen = false;
    this.cvPreviewPath = '';
  }
}
