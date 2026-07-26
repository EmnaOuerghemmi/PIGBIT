import { Component, HostListener, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.css']
})
export class RegisterComponent {
  firstName: string = '';
  lastName: string = '';
  username: string = '';
  email: string = '';
  password: string = '';
  confirmPassword: string = '';
  role: string = 'READ_ONLY';
  showPassword: boolean = false;
  showConfirm: boolean = false;
  isLoading: boolean = false;
  errorMessage: string = '';
  currentYear: number = new Date().getFullYear();

  roles = [
    { value: 'READ_ONLY', label: 'Lecteur (accès en lecture)' },
    { value: 'RH_STAFF', label: 'Agent RH (base)' },
    { value: 'RH_MANAGER', label: 'Manager RH (avancé)' },
    { value: 'ADMIN', label: 'Administrateur (tous les droits)' }
  ];

  leftEyeStyle = { transform: 'translate(0px, 0px)' };
  rightEyeStyle = { transform: 'translate(0px, 0px)' };

  @ViewChild('leftEye') leftEyeRef!: ElementRef;
  @ViewChild('rightEye') rightEyeRef!: ElementRef;

  constructor(private authService: AuthService, private router: Router) {}

  @HostListener('document:mousemove', ['$event'])
  onMouseMove(event: MouseEvent): void {
    this.moveEye(this.leftEyeRef, event, this.leftEyeStyle);
    this.moveEye(this.rightEyeRef, event, this.rightEyeStyle);
  }

  private moveEye(eyeRef: ElementRef, event: MouseEvent, styleObj: any): void {
    if (!eyeRef?.nativeElement) return;
    const rect = eyeRef.nativeElement.getBoundingClientRect();
    const dx = event.clientX - (rect.left + rect.width / 2);
    const dy = event.clientY - (rect.top + rect.height / 2);
    const dist = Math.min(Math.hypot(dx, dy), 6);
    const angle = Math.atan2(dy, dx);
    styleObj.transform = `translate(${Math.cos(angle) * dist}px, ${Math.sin(angle) * dist}px)`;
  }

  register(): void {
    if (!this.firstName || !this.lastName || !this.username || !this.email || !this.password || !this.role) {
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
    this.authService.register({
      email: this.email,
      username: this.username,
      password: this.password,
      full_name: `${this.firstName} ${this.lastName}`.trim(),
      role: this.role
    }).subscribe({
      next: () => {
        this.isLoading = false;
        this.router.navigate(['/login']);
      },
      error: (err: any) => {
        this.isLoading = false;
        this.errorMessage = err?.error?.detail || err?.error?.message || 'Échec de l\'inscription. Veuillez réessayer.';
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
