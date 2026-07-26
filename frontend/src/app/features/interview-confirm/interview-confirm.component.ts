import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { RecruitmentService, PublicInvitationView, InterviewSlot } from '../../core/services/recruitment.service';

@Component({
  selector: 'app-interview-confirm',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './interview-confirm.component.html',
  styleUrl: './interview-confirm.component.css'
})
export class InterviewConfirmComponent implements OnInit {
  token = '';
  invitation: PublicInvitationView | null = null;
  selectedSlotId: string | null = null;
  loading = true;
  submitting = false;
  errorMsg = '';
  serverError = '';

  constructor(
    private route: ActivatedRoute,
    private recruitment: RecruitmentService,
  ) {}

  ngOnInit() {
    this.token = this.route.snapshot.paramMap.get('token') || '';
    if (!this.token) {
      this.errorMsg = 'Lien invalide.';
      this.loading = false;
      return;
    }
    this.load();
  }

  load() {
    this.loading = true;
    this.serverError = '';
    this.recruitment.getPublicInvitation(this.token).subscribe({
      next: data => {
        this.invitation = data;
        if (data.confirmed_slot) this.selectedSlotId = data.confirmed_slot.id;
        this.loading = false;
      },
      error: err => {
        this.errorMsg = err?.error?.detail || 'Invitation introuvable ou expirée.';
        this.loading = false;
      }
    });
  }

  select(slot: InterviewSlot) {
    if (this.isClosed || slot.is_selected) return;
    this.selectedSlotId = slot.id;
    this.serverError = '';
  }

  confirm() {
    if (!this.selectedSlotId || !this.invitation || this.isClosed) return;
    this.submitting = true;
    this.serverError = '';
    this.recruitment.confirmInvitationSlot(this.token, this.selectedSlotId).subscribe({
      next: data => {
        this.invitation = data;
        this.submitting = false;
      },
      error: err => {
        this.serverError = err?.error?.detail || 'Erreur lors de la confirmation.';
        this.submitting = false;
      }
    });
  }

  get isExpired(): boolean { return this.invitation?.status === 'EXPIRED'; }
  get isCancelled(): boolean { return this.invitation?.status === 'CANCELLED'; }
  get isConfirmed(): boolean { return this.invitation?.status === 'CONFIRMED'; }
  get isPending(): boolean { return this.invitation?.status === 'PENDING'; }
  get isClosed(): boolean { return this.isExpired || this.isCancelled || this.isConfirmed; }

  // ─── Formatting helpers ───
  formatDate(iso: string): string {
    const d = new Date(iso);
    const days = ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'];
    const months = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin',
                    'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
    return `${days[d.getDay()]} ${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
  }

  formatTime(iso: string): string {
    const d = new Date(iso);
    return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  }

  duration(start: string, end: string): number {
    return Math.round((new Date(end).getTime() - new Date(start).getTime()) / 60000);
  }

  expiresIn(iso: string): string {
    const ms = new Date(iso).getTime() - Date.now();
    if (ms <= 0) return 'expiré';
    const h = Math.floor(ms / 3_600_000);
    const m = Math.floor((ms % 3_600_000) / 60_000);
    if (h >= 24) return `${Math.floor(h / 24)} jour${Math.floor(h / 24) > 1 ? 's' : ''}`;
    if (h > 0)   return `${h}h${m.toString().padStart(2, '0')}`;
    return `${m} min`;
  }
}
