import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ContractService, Contract, ContractStats } from '../../../core/services/contract.service';

@Component({
  selector: 'app-contracts',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './contracts.component.html',
  styleUrls: ['./contracts.component.css'],
})
export class ContractsComponent implements OnInit {
  contracts: Contract[] = [];
  stats: ContractStats | null = null;
  loading = true;
  error = '';
  statusFilter = '';

  // Édition inline du brouillon
  editing: Contract | null = null;
  editModel: Partial<Contract> = {};
  saving = false;

  copiedId: string | null = null;
  downloadingId: string | null = null;
  sendingId: string | null = null;

  types = ['CDI', 'CDD', 'STAGE', 'ALTERNANCE'];

  constructor(private contractsSvc: ContractService) {}

  ngOnInit(): void { this.load(); }

  load(): void {
    this.loading = true;
    this.error = '';
    this.contractsSvc.list(this.statusFilter || undefined).subscribe({
      next: (rows) => { this.contracts = rows; this.loading = false; },
      error: (err) => { this.loading = false; this.error = err?.error?.detail || 'Chargement impossible.'; },
    });
    this.contractsSvc.stats().subscribe({ next: (s) => (this.stats = s) });
  }

  // ── Édition brouillon ───────────────────────────────────────────────────────
  startEdit(c: Contract): void {
    this.editing = c;
    this.editModel = {
      contract_type: c.contract_type, position: c.position, department: c.department,
      salary: c.salary, trial_period_months: c.trial_period_months, weekly_hours: c.weekly_hours,
      start_date: c.start_date ? (c.start_date.slice(0, 10) as any) : null,
      notes: c.notes,
      employee_birth_date: c.employee_birth_date ? (c.employee_birth_date.slice(0, 10) as any) : null,
      employee_cin: c.employee_cin,
      employee_cin_issue_date: c.employee_cin_issue_date ? (c.employee_cin_issue_date.slice(0, 10) as any) : null,
      employee_address: c.employee_address,
    };
  }
  cancelEdit(): void { this.editing = null; this.editModel = {}; }

  saveEdit(): void {
    if (!this.editing) return;
    this.saving = true;
    this.contractsSvc.update(this.editing.id, this.editModel).subscribe({
      next: () => { this.saving = false; this.cancelEdit(); this.load(); },
      error: (err) => { this.saving = false; this.error = err?.error?.detail || 'Enregistrement impossible.'; },
    });
  }

  // ── Actions ─────────────────────────────────────────────────────────────────
  send(c: Contract): void {
    this.sendingId = c.id;
    this.contractsSvc.send(c.id).subscribe({
      next: () => { this.sendingId = null; this.load(); },
      error: (err) => { this.sendingId = null; alert(err?.error?.detail || 'Envoi impossible.'); },
    });
  }

  copyLink(c: Contract): void {
    if (!c.public_url) return;
    navigator.clipboard?.writeText(c.public_url).then(() => {
      this.copiedId = c.id;
      setTimeout(() => { if (this.copiedId === c.id) this.copiedId = null; }, 2500);
    });
  }

  downloadPdf(c: Contract): void {
    this.downloadingId = c.id;
    this.contractsSvc.downloadPdf(c.id).subscribe({
      next: (blob) => {
        this.downloadingId = null;
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `Contrat_${(c.candidate_name || 'candidat').replace(/\s+/g, '_')}.pdf`;
        a.click(); URL.revokeObjectURL(url);
      },
      error: () => { this.downloadingId = null; },
    });
  }

  remove(c: Contract): void {
    if (!confirm(`Supprimer ce contrat brouillon pour ${c.candidate_name} ?`)) return;
    this.contractsSvc.remove(c.id).subscribe({ next: () => this.load() });
  }

  // ── Helpers ─────────────────────────────────────────────────────────────────
  statusLabel(s: string): string {
    return ({ DRAFT: 'Brouillon', SENT: 'Envoyé', SIGNED: 'Signé', ACTIVE: 'Actif',
              DECLINED: 'Refusé', EXPIRED: 'Expiré' } as any)[s] || s;
  }
  statusTone(s: string): string {
    return ({ DRAFT: 'muted', SENT: 'info', SIGNED: 'success', ACTIVE: 'success',
              DECLINED: 'danger', EXPIRED: 'warn' } as any)[s] || 'muted';
  }
  trackC(_i: number, c: Contract): string { return c.id; }
}
