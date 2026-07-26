import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RecruitmentService, CVAnalysisResponse } from '../../../core/services/recruitment.service';

@Component({
  selector: 'app-cv-analysis',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './cv-analysis.component.html',
  styleUrls: ['./cv-analysis.component.css']
})
export class CVAnalysisComponent implements OnInit {
  @Input() applicationId: string = '';

  analysisData: CVAnalysisResponse | null = null;
  isLoading = true;

  constructor(private recruitment: RecruitmentService) {}

  ngOnInit() {
    this.loadAnalysis();
  }

  loadAnalysis() {
    if (!this.applicationId) {
      this.isLoading = false;
      return;
    }
    this.recruitment.getExtractedCVData(this.applicationId).subscribe({
      next: (data) => {
        this.analysisData = data;
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
      }
    });
  }

  formatEducation(level: string): string {
    const map: Record<string, string> = {
      NONE: 'Non précisé',
      HIGH_SCHOOL: 'Baccalauréat',
      BACHELOR: 'Licence / Bachelor',
      INGENIEUR: 'Diplôme d\'ingénieur',
      MASTER: 'Master',
      PHD: 'Doctorat',
      phd: 'Doctorat',
      master: 'Master',
      ingenieur: 'Diplôme d\'ingénieur',
      bachelor: 'Licence / Bachelor',
    };
    return map[level] ?? level;
  }

  formatDate(isoDate: string | null): string {
    if (!isoDate) return '-';
    return new Date(isoDate).toLocaleDateString('fr-FR', {
      day: '2-digit', month: 'long', year: 'numeric'
    });
  }
}
