import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CareerService, CareerStats, CareerPlan } from '../../../core/services/career.service';

@Component({
  selector: 'app-career',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './career.component.html',
  styleUrls: ['./career.component.css']
})
export class CareerComponent implements OnInit {
  stats: CareerStats | null = null;
  plans: CareerPlan[] = [];
  loading = false;

  constructor(private career: CareerService) {}

  ngOnInit(): void {
    this.loading = true;
    this.career.getStats().subscribe({
      next: s => this.stats = s,
      error: () => {},
    });
    this.career.getPlans().subscribe({
      next: p => { this.plans = p; this.loading = false; },
      error: () => this.loading = false,
    });
  }

  statusLabel(status: string): string {
    const labels: Record<string, string> = {
      PROBATION: 'Période d\'essai',
      IN_PROGRESS: 'En cours',
      PROMOTION_PLANNED: 'Promotion prévue',
      COMPLETED: 'Terminé',
      RETIREMENT_PLANNED: 'Retraite prévue',
    };
    return labels[status] || status;
  }
}
