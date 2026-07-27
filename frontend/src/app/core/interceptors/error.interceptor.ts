import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';

import { ToastService } from '../services/toast.service';

/**
 * Traduit les échecs HTTP techniques en messages compréhensibles.
 *
 * Ne fait qu'AJOUTER une notification : l'erreur est systématiquement
 * relancée, afin que les composants gardent la main sur leur propre logique
 * (arrêt d'un indicateur de chargement, message contextuel, etc.).
 *
 * Deux familles sont volontairement ignorées ici :
 *   - 401, géré par jwtInterceptor qui tente un rafraîchissement de jeton
 *     transparent ; afficher « non authentifié » ferait clignoter un message
 *     alarmant alors que la requête va aboutir après renouvellement.
 *   - 422 et 400, qui portent des erreurs de validation de formulaire : elles
 *     doivent s'afficher au niveau du champ concerné, pas dans un toast
 *     détaché du contexte.
 */
export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const toast = inject(ToastService);

  return next(req).pipe(
    catchError((err: HttpErrorResponse) => {
      const message = describe(err);
      if (message) {
        toast.error(message);
      }
      return throwError(() => err);
    })
  );
};

function describe(err: HttpErrorResponse): string | null {
  // Erreur réseau / serveur injoignable : `status` vaut 0.
  if (err.status === 0) {
    return 'Serveur injoignable. Vérifiez votre connexion.';
  }

  const detail =
    typeof err.error?.detail === 'string' ? err.error.detail : null;

  switch (err.status) {
    case 400:
    case 401:
    case 422:
      return null; // traités ailleurs (cf. commentaire d'en-tête)

    case 403:
      return detail ?? "Vous n'avez pas les droits nécessaires pour cette action.";

    case 404:
      return detail ?? 'Ressource introuvable.';

    case 409:
      return detail ?? 'Conflit : cette ressource existe déjà ou a été modifiée.';

    case 413:
      return 'Fichier trop volumineux.';

    case 429:
      // Le backend renseigne Retry-After sur les routes limitées.
      return detail ?? 'Trop de tentatives. Patientez avant de réessayer.';

    default:
      if (err.status >= 500) {
        // Le détail d'une 500 est une trace technique : inutile à
        // l'utilisateur, et potentiellement révélateur d'informations internes.
        return 'Une erreur serveur est survenue. Réessayez dans un instant.';
      }
      return detail ?? 'Une erreur est survenue.';
  }
}
