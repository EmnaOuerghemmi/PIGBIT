import { Component, OnInit, OnDestroy, HostListener, ElementRef, ViewChild, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { GoogleService } from '../../../core/services/google.service';
import { RoleRedirectService } from '../../../core/services/role-redirect.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent implements OnInit, AfterViewInit, OnDestroy {
  email: string = '';
  password: string = '';
  showPassword: boolean = false;
  isLoading: boolean = false;
  errorMessage: string = '';

  /** Passe à true quand le backend réclame le second facteur. */
  needsTotp: boolean = false;
  totpCode: string = '';
  currentYear: number = new Date().getFullYear();

  // Eye tracking
  leftEyeStyle = { transform: 'translate(0px, 0px)' };
  rightEyeStyle = { transform: 'translate(0px, 0px)' };

  @ViewChild('leftEye') leftEyeRef!: ElementRef;
  @ViewChild('rightEye') rightEyeRef!: ElementRef;

  constructor(
    private authService: AuthService,
    private googleService: GoogleService,
    private router: Router,
    private roleRedirectService: RoleRedirectService
  ) {}

  ngOnInit(): void {
    // Initialize Google Sign-In listener
    this.googleService.credentialResponse.subscribe((idToken: string) => {
      this.loginWithGoogle(idToken);
    });
  }

  ngAfterViewInit(): void {
    // Render Google button after view is initialized
    setTimeout(() => {
      this.googleService.renderButton('google-signin-button', { iconOnly: true });
    }, 100);
  }

  ngOnDestroy(): void {}

  @HostListener('document:mousemove', ['$event'])
  onMouseMove(event: MouseEvent): void {
    this.moveEye(this.leftEyeRef, event, this.leftEyeStyle);
    this.moveEye(this.rightEyeRef, event, this.rightEyeStyle);
  }

  private moveEye(eyeRef: ElementRef, event: MouseEvent, styleObj: any): void {
    if (!eyeRef?.nativeElement) return;
    const eye = eyeRef.nativeElement;
    const rect = eye.getBoundingClientRect();
    const eyeCX = rect.left + rect.width / 2;
    const eyeCY = rect.top + rect.height / 2;
    const dx = event.clientX - eyeCX;
    const dy = event.clientY - eyeCY;
    const angle = Math.atan2(dy, dx);
    const dist = Math.min(Math.hypot(dx, dy), 6);
    styleObj.transform = `translate(${Math.cos(angle) * dist}px, ${Math.sin(angle) * dist}px)`;
  }

  togglePassword(): void {
    this.showPassword = !this.showPassword;
  }

  login(): void {
    if (!this.email || !this.password) {
      this.errorMessage = 'Veuillez remplir tous les champs.';
      return;
    }
    if (this.needsTotp && !this.totpCode) {
      this.errorMessage = 'Saisissez le code de votre application d\'authentification.';
      return;
    }
    this.isLoading = true;
    this.errorMessage = '';
    // `totpCode` reste vide au premier appel : le backend indique alors, par
    // un 401 « 2FA code required. », que le compte est protégé.
    this.authService.login(this.email, this.password, this.totpCode || undefined).subscribe({
      next: (response: any) => {
        this.isLoading = false;
        if (response?.access_token) {
          this.authService.setToken(response.access_token);
          if (response.refresh_token) {
            this.authService.setRefreshToken(response.refresh_token);
          }
          this.authService.loadCurrentUser().subscribe(() => {
            // Use RoleRedirectService to redirect to appropriate dashboard
            this.roleRedirectService.redirectBasedOnRole();
          });
        }
      },
      error: (error: any) => {
        this.isLoading = false;
        const detail: string = error?.error?.detail || error?.error?.message || '';

        // Bascule vers l'étape 2FA plutôt que d'afficher « identifiants
        // invalides » : les identifiants sont bons, il manque le second facteur.
        if (detail.includes('2FA code required')) {
          this.needsTotp = true;
          this.errorMessage = '';
          return;
        }
        if (detail.includes('Invalid 2FA code')) {
          this.needsTotp = true;
          this.totpCode = '';
          this.errorMessage = 'Code incorrect. Vérifiez l\'heure de votre téléphone et réessayez.';
          return;
        }
        this.errorMessage = detail || 'Identifiants invalides. Veuillez réessayer.';
      }
    });
  }

  /** Revient à l'écran mot de passe (mauvais compte, ou abandon de la 2FA). */
  cancelTotp(): void {
    this.needsTotp = false;
    this.totpCode = '';
    this.errorMessage = '';
  }

  /** Les codes TOTP sont numériques et à 6 chiffres. */
  onTotpInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    input.value = input.value.replace(/\D/g, '').slice(0, 6);
    this.totpCode = input.value;
  }

  loginWithGoogle(idToken: string): void {
    this.isLoading = true;
    this.errorMessage = '';
    this.authService.loginWithGoogle(idToken).subscribe({
      next: (response: any) => {
        this.isLoading = false;
        if (response?.access_token) {
          this.authService.setToken(response.access_token);
          if (response.refresh_token) {
            this.authService.setRefreshToken(response.refresh_token);
          }
          this.authService.loadCurrentUser().subscribe(() => {
            this.roleRedirectService.redirectBasedOnRole();
          });
        }
      },
      error: (error: any) => {
        this.isLoading = false;
        this.errorMessage = error?.error?.detail || error?.error?.message || 'Erreur de connexion Google. Veuillez réessayer.';
      }
    });
  }
}
