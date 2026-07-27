import { Injectable, signal } from '@angular/core';

export interface ConfirmOptions {
  title: string;
  message: string;
  /** Libellé du bouton de validation. Défaut : « Confirmer ». */
  confirmLabel?: string;
  cancelLabel?: string;
  /**
   * Présente l'action comme destructive (bouton rouge). À utiliser pour tout
   * ce qui supprime ou est irréversible.
   */
  danger?: boolean;
}

interface PendingConfirm extends ConfirmOptions {
  resolve: (value: boolean) => void;
}

/**
 * Boîte de confirmation applicative, en remplacement de `window.confirm()`.
 *
 * Conserve l'ergonomie d'appel du natif — `if (await confirm.ask(...))` — ce
 * qui rend la migration des appels existants directe, sans réécrire la logique
 * autour.
 *
 * Le natif était problématique sur trois points : impossible à styler (rupture
 * visuelle avec le reste de l'interface), il affiche le nom de domaine, et
 * certains navigateurs le suppriment purement et simplement dans les iframes
 * ou après plusieurs appels rapprochés — une suppression pouvait alors être
 * validée sans que l'utilisateur ait rien vu.
 */
@Injectable({ providedIn: 'root' })
export class ConfirmService {
  private readonly _pending = signal<PendingConfirm | null>(null);
  readonly pending = this._pending.asReadonly();

  ask(options: ConfirmOptions): Promise<boolean> {
    // Une confirmation déjà ouverte est refusée plutôt qu'écrasée : sinon sa
    // promesse resterait en attente indéfiniment et l'appelant serait bloqué.
    const current = this._pending();
    if (current) {
      current.resolve(false);
    }
    return new Promise<boolean>((resolve) => {
      this._pending.set({ ...options, resolve });
    });
  }

  /** Raccourci pour les suppressions, le cas le plus fréquent. */
  askDelete(message: string, title = 'Confirmer la suppression'): Promise<boolean> {
    return this.ask({ title, message, confirmLabel: 'Supprimer', danger: true });
  }

  respond(value: boolean): void {
    const current = this._pending();
    if (!current) return;
    this._pending.set(null);
    current.resolve(value);
  }
}
