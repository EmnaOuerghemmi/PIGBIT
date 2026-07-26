import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';
import { UserService } from '../../../core/services/user.service';
import { Router } from '@angular/router';
import { TwoFactorComponent } from '../../auth/two-factor/two-factor.component';

interface UserProfile {
  email: string;
  full_name: string;
  username: string;
  phone?: string;
  location?: string;
  bio?: string;
  created_at?: string;
  is_admin?: boolean;
  is_rh_manager?: boolean;
  is_verified?: boolean;
}

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule, TwoFactorComponent],
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.css']
})
export class ProfileComponent implements OnInit {
  user: UserProfile | null = null;
  userInitial = '';
  successMsg = '';
  errorMsg = '';
  originalUser: UserProfile | null = null;

  constructor(
    private authService: AuthService,
    private userService: UserService,
    private router: Router,
  ) {}

  ngOnInit() {
    const currentUser = this.authService.getCurrentUser();
    if (currentUser) {
      this.user = {
        email: currentUser.email,
        full_name: currentUser.full_name || '',
        username: currentUser.username || '',
        phone: '',
        location: '',
        bio: '',
        created_at: currentUser.created_at
      };
      this.originalUser = JSON.parse(JSON.stringify(this.user));
      this.userInitial = (currentUser.full_name || currentUser.email).charAt(0).toUpperCase();
    } else {
      this.router.navigate(['/login']);
    }
  }

  saveProfile() {
    if (!this.user) return;

    this.userService.updateMe({
      full_name: this.user.full_name,
      phone_number: this.user.phone,
    } as any).subscribe({
      next: () => {
        this.successMsg = 'Profil mis à jour avec succès!';
        this.errorMsg = '';
        this.originalUser = JSON.parse(JSON.stringify(this.user));
        setTimeout(() => (this.successMsg = ''), 3000);
      },
      error: err => {
        this.errorMsg = err.error?.detail || 'Échec de la mise à jour du profil.';
        this.successMsg = '';
      },
    });
  }

  resetForm() {
    if (this.originalUser) {
      this.user = JSON.parse(JSON.stringify(this.originalUser));
    }
    this.successMsg = '';
    this.errorMsg = '';
  }

  changePassword() {
    const current = window.prompt('Mot de passe actuel :');
    if (!current) return;
    const next = window.prompt('Nouveau mot de passe (8+ caractères, maj/min/chiffre/spécial) :');
    if (!next) return;

    this.userService.changePassword(current, next).subscribe({
      next: () => {
        this.successMsg = 'Mot de passe modifié avec succès.';
        this.errorMsg = '';
        setTimeout(() => (this.successMsg = ''), 3000);
      },
      error: err => {
        this.errorMsg = err.error?.detail || 'Échec du changement de mot de passe.';
        this.successMsg = '';
      },
    });
  }

  deleteAccount() {
    const confirm = window.confirm(
      'Êtes-vous sûr de vouloir supprimer votre compte ? Cette action ne peut pas être annulée.'
    );
    if (!confirm) return;

    const confirmAgain = window.confirm(
      'Veuillez confirmer une deuxième fois. Toutes vos données seront supprimées.'
    );
    if (!confirmAgain) return;

    this.userService.deleteMe().subscribe({
      next: () => {
        alert('Votre compte a été supprimé.');
        this.authService.clearSession();
        this.router.navigate(['/register']);
      },
      error: err => {
        this.errorMsg = err.error?.detail || 'Échec de la suppression du compte.';
      },
    });
  }
}
