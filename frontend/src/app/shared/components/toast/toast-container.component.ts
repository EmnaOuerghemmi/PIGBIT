import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';

import { ToastService } from '../../../core/services/toast.service';

/**
 * Pile de notifications, montée une seule fois à la racine de l'application.
 *
 * `aria-live="polite"` : les lecteurs d'écran annoncent les messages sans
 * interrompre la tâche en cours — un `alert()` natif, lui, volait le focus.
 */
@Component({
  selector: 'app-toast-container',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './toast-container.component.html',
  styleUrls: ['./toast-container.component.css'],
})
export class ToastContainerComponent {
  private toastService = inject(ToastService);
  readonly toasts = this.toastService.toasts;

  dismiss(id: number): void {
    this.toastService.dismiss(id);
  }
}
