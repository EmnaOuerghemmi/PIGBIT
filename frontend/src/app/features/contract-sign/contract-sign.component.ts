import { Component, ElementRef, OnInit, ViewChild, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { ContractService, PublicContract } from '../../core/services/contract.service';

@Component({
  selector: 'app-contract-sign',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './contract-sign.component.html',
  styleUrls: ['./contract-sign.component.css'],
})
export class ContractSignComponent implements OnInit, AfterViewInit {
  @ViewChild('pad') padRef?: ElementRef<HTMLCanvasElement>;

  token = '';
  contract: PublicContract | null = null;
  loading = true;
  error = '';

  // Formulaire de signature
  signerName = '';
  consent = false;
  submitting = false;
  hasDrawn = false;

  // Refus
  showDecline = false;
  declineReason = '';

  private ctx?: CanvasRenderingContext2D;
  private drawing = false;

  constructor(private route: ActivatedRoute, private contracts: ContractService) {}

  ngOnInit(): void {
    this.token = this.route.snapshot.paramMap.get('token') || '';
    this.contracts.getPublic(this.token).subscribe({
      next: (c) => {
        this.contract = c;
        this.signerName = c.candidate_name;
        this.loading = false;
        setTimeout(() => this.initCanvas(), 0);
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'Contrat introuvable ou lien expiré.';
      },
    });
  }

  ngAfterViewInit(): void { this.initCanvas(); }

  get isSignable(): boolean {
    return this.contract?.status === 'SENT';
  }

  // ── Canvas signature ────────────────────────────────────────────────────────

  private initCanvas(): void {
    const canvas = this.padRef?.nativeElement;
    if (!canvas || !this.isSignable) return;
    // Résolution nette (retina).
    const ratio = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * ratio;
    canvas.height = rect.height * ratio;
    const ctx = canvas.getContext('2d')!;
    ctx.scale(ratio, ratio);
    ctx.lineWidth = 2.2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = '#0A1B18';
    this.ctx = ctx;
  }

  private pos(e: MouseEvent | TouchEvent): { x: number; y: number } {
    const canvas = this.padRef!.nativeElement;
    const rect = canvas.getBoundingClientRect();
    const p = 'touches' in e ? e.touches[0] : e;
    return { x: p.clientX - rect.left, y: p.clientY - rect.top };
  }

  startDraw(e: MouseEvent | TouchEvent): void {
    if (!this.ctx) return;
    e.preventDefault();
    this.drawing = true;
    const { x, y } = this.pos(e);
    this.ctx.beginPath();
    this.ctx.moveTo(x, y);
  }
  moveDraw(e: MouseEvent | TouchEvent): void {
    if (!this.drawing || !this.ctx) return;
    e.preventDefault();
    const { x, y } = this.pos(e);
    this.ctx.lineTo(x, y);
    this.ctx.stroke();
    this.hasDrawn = true;
  }
  endDraw(): void { this.drawing = false; }

  clearPad(): void {
    const canvas = this.padRef?.nativeElement;
    if (canvas && this.ctx) {
      this.ctx.clearRect(0, 0, canvas.width, canvas.height);
      this.hasDrawn = false;
    }
  }

  // ── Actions ─────────────────────────────────────────────────────────────────

  sign(): void {
    if (!this.canSubmit) return;
    const dataUrl = this.padRef!.nativeElement.toDataURL('image/png');
    this.submitting = true;
    this.error = '';
    this.contracts.sign(this.token, {
      signer_name: this.signerName.trim(),
      signature_image: dataUrl,
      consent: this.consent,
    }).subscribe({
      next: (c) => { this.contract = c; this.submitting = false; },
      error: (err) => {
        this.submitting = false;
        this.error = err?.error?.detail || 'La signature a échoué. Réessayez.';
      },
    });
  }

  get canSubmit(): boolean {
    return this.isSignable && !this.submitting
        && this.signerName.trim().length >= 2 && this.consent && this.hasDrawn;
  }

  confirmDecline(): void {
    this.submitting = true;
    this.contracts.decline(this.token, this.declineReason.trim()).subscribe({
      next: (c) => { this.contract = c; this.submitting = false; this.showDecline = false; },
      error: (err) => {
        this.submitting = false;
        this.error = err?.error?.detail || 'Action impossible.';
      },
    });
  }

  typeLabel(t?: string): string {
    return ({ CDI: 'CDI', CDD: 'CDD', STAGE: 'Stage', ALTERNANCE: 'Alternance' } as any)[t || ''] || t;
  }
}
