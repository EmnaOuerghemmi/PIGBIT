import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, ActivatedRoute } from '@angular/router';
import { PasswordService } from '../../../core/services/password.service';

@Component({
  selector: 'app-verify-email',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './verify-email.component.html',
  styleUrl: './verify-email.component.css'
})
export class VerifyEmailComponent implements OnInit {
  token: string = '';
  isLoading: boolean = true;
  isSuccess: boolean = false;
  errorMessage: string = '';
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
        this.isLoading = false;
        this.errorMessage = 'Token de vérification invalide ou manquant.';
        return;
      }

      this.verifyEmail();
    });
  }

  verifyEmail(): void {
    this.passwordService.verifyEmail(this.token).subscribe({
      next: (response) => {
        this.isLoading = false;
        this.isSuccess = true;
        setTimeout(() => {
          this.router.navigate(['/login']);
        }, 3000);
      },
      error: (error) => {
        this.isLoading = false;
        this.errorMessage = error?.error?.detail || error?.error?.message || 'Erreur lors de la vérification de l\'email.';
      }
    });
  }
}
