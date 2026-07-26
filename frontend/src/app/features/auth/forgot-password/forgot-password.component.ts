import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { PasswordService } from '../../../core/services/password.service';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './forgot-password.component.html',
  styleUrl: './forgot-password.component.css'
})
export class ForgotPasswordComponent {
  email: string = '';
  isLoading: boolean = false;
  errorMessage: string = '';
  successMessage: string = '';
  currentYear: number = new Date().getFullYear();

  constructor(private passwordService: PasswordService, private router: Router) {}

  requestReset(): void {
    if (!this.email) {
      this.errorMessage = 'Veuillez entrer votre email.';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.successMessage = '';

    this.passwordService.forgotPassword(this.email).subscribe({
      next: (response) => {
        this.isLoading = false;
        this.successMessage = 'Un lien de réinitialisation a été envoyé à votre email. Veuillez vérifier votre boîte de réception (et dossier spam).';
        this.email = '';
      },
      error: (error) => {
        this.isLoading = false;
        this.errorMessage = error?.error?.detail || error?.error?.message || 'Une erreur s\'est produite. Veuillez réessayer.';
      }
    });
  }
}
