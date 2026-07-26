import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RecruitmentService } from '../../../core/services/recruitment.service';

@Component({
  selector: 'app-interview-scheduler',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './interview-scheduler.component.html',
  styleUrl: './interview-scheduler.component.css'
})
export class InterviewSchedulerComponent {
  @Input() applicationId: string = '';
  @Input() jobTitle: string = '';

  @Output() closed = new EventEmitter<boolean>();

  slots: string[] = ['', '', ''];
  message = '';
  isSubmitting = false;
  success = false;
  errorMsg = '';

  constructor(private recruitment: RecruitmentService) {}

  addSlot() {
    if (this.slots.length < 5) this.slots.push('');
  }

  removeSlot(i: number) {
    if (this.slots.length > 1) this.slots.splice(i, 1);
  }

  get validSlots(): string[] {
    return this.slots.filter(s => s.trim().length > 0);
  }

  trackByIndex(i: number) { return i; }

  submit() {
    if (this.validSlots.length === 0) {
      this.errorMsg = 'Veuillez saisir au moins un créneau.';
      return;
    }
    this.isSubmitting = true;
    this.errorMsg = '';

    // The datetime-local input produces "2026-06-11T09:00" in the user's
    // local TZ. We pass it straight through — Pydantic accepts ISO-8601
    // and FastAPI normalises it server-side.
    const isoSlots = this.validSlots.map(s => new Date(s).toISOString());

    this.recruitment.scheduleInterview(this.applicationId, isoSlots, this.message).subscribe({
      next: () => {
        this.isSubmitting = false;
        this.success = true;
        setTimeout(() => this.closed.emit(true), 1600);
      },
      error: (err) => {
        this.isSubmitting = false;
        this.errorMsg = err?.error?.detail || 'Erreur lors de la planification.';
      }
    });
  }

  cancel() { this.closed.emit(false); }
}
