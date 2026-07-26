import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RecruitmentService, CandidateScoreResponse, ScoreDetails } from '../../../core/services/recruitment.service';

@Component({
  selector: 'app-score-breakdown',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './score-breakdown.component.html',
  styleUrls: ['./score-breakdown.component.css']
})
export class ScoreBreakdownComponent implements OnInit {
  @Input() applicationId: string = '';

  scoreData: CandidateScoreResponse | null = null;
  isLoading = true;

  constructor(private recruitment: RecruitmentService) {}

  ngOnInit() {
    this.loadScoreBreakdown();
  }

  loadScoreBreakdown() {
    if (!this.applicationId) {
      this.isLoading = false;
      return;
    }
    this.recruitment.getScoreBreakdown(this.applicationId).subscribe({
      next: (data) => {
        this.scoreData = data;
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
      }
    });
  }

  get details(): ScoreDetails | null {
    return this.scoreData?.score_details ?? null;
  }

  getScoreClass(): string {
    if (!this.scoreData) return '';
    const s = this.scoreData.total_score;
    if (s >= 80) return 'excellent';
    if (s >= 60) return 'good';
    if (s >= 40) return 'average';
    return 'poor';
  }

  getScoreLabel(): string {
    const s = this.scoreData?.total_score ?? 0;
    if (s >= 80) return 'Excellent profil';
    if (s >= 60) return 'Bon candidat';
    if (s >= 40) return 'Profil à surveiller';
    return 'Profil à réviser';
  }
}
