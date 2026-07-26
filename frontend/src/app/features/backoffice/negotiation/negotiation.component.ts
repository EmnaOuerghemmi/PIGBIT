import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import {
  NegotiationService, JobData, NegotiationRequest, NegotiationMessage,
} from '../../../services/negotiation.service';
import { RecruitmentService, JobOffer } from '../../../core/services/recruitment.service';

interface NegotiationEvent { icon: string; text: string; }

@Component({
  selector: 'app-negotiation',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './negotiation.component.html',
  styleUrls: ['./negotiation.component.css'],
})
export class NegotiationComponent implements OnInit, OnDestroy {
  jobs: JobOffer[] = [];
  selectedJobId = '';
  employerOffer: number | null = 3000;

  running = false;
  error = '';
  result: any = null;          // outcome from /negotiations/initiate
  events: NegotiationEvent[] = [];

  private destroy$ = new Subject<void>();

  constructor(
    private negotiation: NegotiationService,
    private recruitment: RecruitmentService,
  ) {}

  ngOnInit(): void {
    this.recruitment.getJobs(1, 100).subscribe({
      next: res => {
        this.jobs = res.items;
        if (!this.selectedJobId && this.jobs.length) this.selectedJobId = this.jobs[0].id;
      },
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.negotiation.disconnectWebSocket();
  }

  get selectedJob(): JobOffer | undefined {
    return this.jobs.find(j => j.id === this.selectedJobId);
  }

  launch(): void {
    const job = this.selectedJob;
    if (!job || !this.employerOffer || this.employerOffer <= 0) return;

    const skills = (job.required_skills || []).join(' ').toLowerCase();
    const jobData: JobData = {
      job_id: job.id,
      title: job.title,
      description: job.description || '',
      rating: 4,
      experience_years: job.required_experience_years ?? null,
      skills_text: (job.required_skills || []).join(', '),
      python: skills.includes('python') ? 1 : 0,
      spark: skills.includes('spark') ? 1 : 0,
      aws: skills.includes('aws') ? 1 : 0,
      excel: skills.includes('excel') ? 1 : 0,
    };
    const request: NegotiationRequest = {
      candidate_id: 'sim-' + Date.now(),
      job_data: jobData,
      employer_offer: this.employerOffer,
    };

    this.running = true;
    this.error = '';
    this.result = null;
    this.events = [];

    this.negotiation.initiateNegotiation(request)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (res: any) => {
          this.running = false;
          this.result = res;
          this.buildEvents(res);
        },
        error: (err) => {
          this.running = false;
          this.error = err?.error?.detail || 'La négociation a échoué. Réessayez.';
        },
      });
  }

  private buildEvents(res: any): void {
    const ev: NegotiationEvent[] = [];
    ev.push({ icon: '📊', text: `Salaire prédit : ${res.predicted_salary ?? '?'} TND (confiance ${Math.round((res.confidence ?? 0) * 100)}%)` });
    ev.push({ icon: '💼', text: `Offre initiale de l'employeur : ${res.initial_offer ?? this.employerOffer} TND` });

    const counters = res.summary?.counter_offers || [];
    counters.forEach((c: any, i: number) => {
      ev.push({ icon: '📤', text: `Tour ${i + 1} : contre-proposition ${Math.round(c.amount)} TND` });
    });
    (res.summary?.decision_history || []).forEach((d: any) => {
      ev.push({ icon: '🤔', text: d.reason });
    });

    ev.push({
      icon: this.statusIcon(res.negotiation_status),
      text: `${this.statusLabel(res.negotiation_status)} — salaire final ${res.final_salary} TND`,
    });
    this.events = ev;
  }

  statusLabel(s: string): string {
    return ({ ACCEPTED: 'Accord trouvé', REJECTED: 'Offre rejetée', COMPROMIS: 'Compromis' } as any)[s] || s || '—';
  }
  statusIcon(s: string): string {
    return ({ ACCEPTED: '✅', REJECTED: '❌', COMPROMIS: '🤝' } as any)[s] || '🔔';
  }
  statusTone(s: string): string {
    return ({ ACCEPTED: 'success', REJECTED: 'danger', COMPROMIS: 'warn' } as any)[s] || 'info';
  }
  gain(): number {
    if (!this.result) return 0;
    return Math.round((this.result.final_salary || 0) - (this.result.initial_offer || this.employerOffer || 0));
  }
}
