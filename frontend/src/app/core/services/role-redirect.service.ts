import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from './auth.service';

@Injectable({
  providedIn: 'root'
})
export class RoleRedirectService {
  constructor(private authService: AuthService, private router: Router) {}

  /**
   * Redirect user based on their role after login
   */
  redirectBasedOnRole(): void {
    const user = this.authService.getCurrentUser();
    
    if (!user) {
      this.router.navigate(['/login']);
      return;
    }

    // Admin and RH roles go to backoffice
    if (user.role === 'ADMIN' || user.role === 'RH_MANAGER' || user.role === 'RH_STAFF') {
      this.router.navigate(['/admin']);
    } else {
      // Other roles (candidates) go to frontoffice home
      this.router.navigate(['/frontoffice/home']);
    }
  }

  /**
   * Check if user is admin/RH
   */
  isAdminOrRH(): boolean {
    const user = this.authService.getCurrentUser();
    if (!user) return false;
    return user.role === 'ADMIN' || user.role === 'RH_MANAGER' || user.role === 'RH_STAFF';
  }

  /**
   * Check if user is candidate
   */
  isCandidate(): boolean {
    const user = this.authService.getCurrentUser();
    if (!user) return false;
    return user.role === 'READ_ONLY' || !['ADMIN', 'RH_MANAGER', 'RH_STAFF'].includes(user.role);
  }
}
