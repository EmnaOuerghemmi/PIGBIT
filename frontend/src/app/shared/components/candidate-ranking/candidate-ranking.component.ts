import { Component, Input, OnInit, OnChanges, SimpleChanges, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RecruitmentService, CandidateRanking } from '../../../core/services/recruitment.service';

export interface WorkflowAction {
  applicationId: string;
  candidateId: string;
  score: number;
}

@Component({
  selector: 'app-candidate-ranking',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './candidate-ranking.component.html',
  styleUrls: ['./candidate-ranking.component.css']
})
export class CandidateRankingComponent implements OnInit, OnChanges {
  @Input() jobId: string = '';
  /** Bump this number from the parent to force a reload (e.g. after scheduling
   *  an interview, so the button state refreshes). */
  @Input() refreshTrigger: number = 0;

  @Output() scheduleInterview = new EventEmitter<WorkflowAction>();
  @Output() startNegotiation  = new EventEmitter<WorkflowAction>();
  @Output() rejectCandidate   = new EventEmitter<WorkflowAction>();

  candidates: CandidateRanking[] = [];
  isLoading = true;
  /** IDs (application_id) of the cards currently expanded to show details. */
  private expandedIds = new Set<string>();

  constructor(private recruitment: RecruitmentService) {}

  ngOnInit() {
    this.loadRanking();
  }

  ngOnChanges(changes: SimpleChanges) {
    // Re-fetch when the selected offer changes (user clicks another job) OR
    // when the parent signals a manual refresh.
    const jobChanged = changes['jobId'] && !changes['jobId'].firstChange;
    const refreshed = changes['refreshTrigger'] && !changes['refreshTrigger'].firstChange;
    if ((jobChanged || refreshed) && this.jobId) {
      this.candidates = [];
      this.isLoading = true;
      this.loadRanking();
    }
  }

  loadRanking() {
    if (!this.jobId) { this.isLoading = false; return; }
    this.recruitment.getRankedCandidates(this.jobId).subscribe({
      next: (response) => {
        this.candidates = response.ranking;
        this.isLoading = false;
      },
      error: () => { this.isLoading = false; }
    });
  }

  isExpanded(c: CandidateRanking): boolean {
    return this.expandedIds.has(c.application_id);
  }

  toggleExpanded(c: CandidateRanking) {
    if (this.expandedIds.has(c.application_id)) {
      this.expandedIds.delete(c.application_id);
    } else {
      this.expandedIds.add(c.application_id);
    }
  }

  getScoreClass(score: number): string {
    if (score >= 85) return 'excellent';
    if (score >= 60) return 'good';
    if (score >= 30) return 'average';
    return 'poor';
  }

  getScoreLabel(score: number): string {
    if (score >= 85) return '🟢 Excellent';
    if (score >= 60) return '🟡 Bon';
    if (score >= 30) return '🟠 Moyen';
    return '🔴 Faible';
  }

  onNegotiate(c: CandidateRanking) {
    this.startNegotiation.emit({ applicationId: c.application_id, candidateId: c.candidate_id, score: c.total_score });
  }

  onScheduleInterview(c: CandidateRanking) {
    if (this.hasActiveInterview(c)) return;
    this.scheduleInterview.emit({ applicationId: c.application_id, candidateId: c.candidate_id, score: c.total_score });
  }

  onReject(c: CandidateRanking) {
    this.rejectCandidate.emit({ applicationId: c.application_id, candidateId: c.candidate_id, score: c.total_score });
  }

  // ── Interview state helpers ──
  hasActiveInterview(c: CandidateRanking): boolean {
    return c.interview_status === 'PENDING' || c.interview_status === 'CONFIRMED';
  }

  isInterviewConfirmed(c: CandidateRanking): boolean {
    return c.interview_status === 'CONFIRMED';
  }

  isInterviewPending(c: CandidateRanking): boolean {
    return c.interview_status === 'PENDING';
  }

  interviewBadgeLabel(c: CandidateRanking): string {
    if (this.isInterviewConfirmed(c)) return '✓ Entretien confirmé';
    if (this.isInterviewPending(c))   return '⏳ Invitation envoyée';
    return '';
  }
}
