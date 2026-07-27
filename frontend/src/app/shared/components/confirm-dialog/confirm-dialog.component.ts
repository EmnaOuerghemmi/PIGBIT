import { Component, HostListener, inject } from '@angular/core';
import { CommonModule } from '@angular/common';

import { ConfirmService } from '../../../core/services/confirm.service';

/**
 * Boîte de dialogue de confirmation, montée une seule fois à la racine.
 * Le contenu est piloté par ConfirmService.
 */
@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './confirm-dialog.component.html',
  styleUrls: ['./confirm-dialog.component.css'],
})
export class ConfirmDialogComponent {
  private confirmService = inject(ConfirmService);
  readonly pending = this.confirmService.pending;

  confirm(): void {
    this.confirmService.respond(true);
  }

  cancel(): void {
    this.confirmService.respond(false);
  }

  /** Échap annule — comportement attendu de toute boîte modale. */
  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.pending()) {
      this.cancel();
    }
  }
}
