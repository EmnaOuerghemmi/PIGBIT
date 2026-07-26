import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, ActivatedRoute } from '@angular/router';
import { PasswordService } from '../../../core/services/password.service';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './reset-password.component.html',
  styleUrl: './reset-password.component.css'
})
export class ResetPasswordComponent implements OnInit {
  token: string = '';
  password: string = '';
  confirmPassword: string = '';
  showPassword: boolean = false;
  showConfirm: boolean = false;
  isLoading: boolean = false;
  errorMessage: string = '';
  successMessage: string = '';
  currentYear: number = new Date().getFullYear();

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private passwordService: PasswordService
  ) {}

  ngOnInit(): void {
    this.route.queryParams.subscribe(params => {
      this.token = params['token'] || '';
      if (!this.token) {
        this.errorMessage = 'Token de réinitialisation invalide ou expiré.';
      }
    });
  }

  resetPassword(): void {
    if (!this.token) {
      this.errorMessage = 'Token manquant. Veuillez utiliser le lien depuis votre email.';
      return;
    }

    if (!this.password || !this.confirmPassword) {
      this.errorMessage = 'Veuillez remplir tous les champs.';
      return;
    }

    if (this.password !== this.confirmPassword) {
      this.errorMessage = 'Les mots de passe ne correspondent pas.';
      return;
    }

    if (!this.isPasswordValid(this.password)) {
      this.errorMessage = 'Le mot de passe doit contenir au moins 8 caractères avec une majuscule, une minuscule, un chiffre et un caractère spécial.';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.successMessage = '';

    this.passwordService.resetPassword(this.token, this.password).subscribe({
      next: (response) => {
        this.isLoading = false;
        this.successMessage = 'Mot de passe réinitialisé avec succès ! Redirection vers la connexion...';
        setTimeout(() => {
          this.router.navigate(['/login']);
        }, 2000);
      },
      error: (error) => {
        this.isLoading = false;
        this.errorMessage = error?.error?.detail || error?.error?.message || 'Une erreur s\'est produite. Veuillez réessayer.';
      }
    });
  }

  isPasswordValid(p: string): boolean {
    return /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()\-_=+\[\]{};':"\\|,.<>/?]).{8,}$/.test(p);
  }

  get passwordStrength(): number {
    const p = this.password;
    if (!p) return 0;
    let score = 0;
    if (p.length >= 8) score++;
    if (p.length >= 12) score++;
    if (/[A-Z]/.test(p)) score++;
    if (/[0-9]/.test(p)) score++;
    if (/[!@#$%^&*()\-_=+\[\]{};':"\\|,.<>/?]/.test(p)) score++;
    return score;
  }

  get strengthLabel(): string {
    const s = this.passwordStrength;
    if (s <= 1) return 'Faible';
    if (s <= 3) return 'Moyen';
    return 'Fort';
  }
}
