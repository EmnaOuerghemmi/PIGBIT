import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { UserManagementService, User, UserCreate } from '../../../core/services/user-management.service';

@Component({
  selector: 'app-users-management',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './users-management.component.html',
  styleUrls: ['./users-management.component.css']
})
export class UsersManagementComponent implements OnInit {
  // Data
  allUsers: User[] = [];
  filteredUsers: User[] = [];
  paginatedUsers: User[] = [];

  // Filters
  searchQuery = '';
  selectedRole = '';
  sortBy = 'created_at';

  // Pagination
  currentPage = 1;
  pageSize = 10;
  totalPages = 1;
  totalUsers = 0;

  // Loading state
  isLoading = false;
  errorMessage = '';

  // Modal
  showModal = false;
  editingUser: User | null = null;
  formData = this.getEmptyForm();

  constructor(private userService: UserManagementService) {}

  ngOnInit(): void {
    this.loadUsers();
  }

  loadUsers(): void {
    this.isLoading = true;
    this.errorMessage = '';

    // Call the backend API with filters
    let role = this.selectedRole || undefined;
    let search = this.searchQuery || undefined;

    console.log('Loading users with params:', { page: this.currentPage, size: this.pageSize, role, search });

    this.userService.getUsers(this.currentPage, this.pageSize, role, undefined, search).subscribe({
      next: (response) => {
        console.log('Users loaded successfully:', response);
        this.allUsers = response.items;
        this.totalUsers = response.total;
        this.totalPages = Math.ceil(response.total / this.pageSize);
        this.updatePaginatedUsers();
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading users:', error);
        console.error('Error status:', error.status);
        console.error('Error message:', error.message);
        console.error('Error body:', error.error);

        let errorMsg = 'Erreur lors du chargement des utilisateurs';

        if (error.status === 0) {
          errorMsg = 'Impossible de se connecter au serveur. Vérifiez que le backend est en cours d\'exécution sur http://localhost:3000';
        } else if (error.status === 401) {
          errorMsg = 'Non authentifié. Veuillez vous reconnecter';
        } else if (error.status === 403) {
          errorMsg = 'Vous n\'avez pas les permissions pour accéder à cette ressource';
        } else if (error.status === 404) {
          errorMsg = 'Endpoint non trouvé';
        } else if (error.error?.detail) {
          errorMsg = error.error.detail;
        }

        this.errorMessage = errorMsg;
        this.isLoading = false;
      }
    });
  }

  filterUsers(): void {
    this.currentPage = 1;
    this.loadUsers();
  }

  sortUsers(): void {
    // Sorting is done on the backend by passing the search/role parameters
    this.currentPage = 1;
    this.loadUsers();
  }

  updatePaginatedUsers(): void {
    this.paginatedUsers = this.allUsers;
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
      this.loadUsers();
    }
  }

  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.loadUsers();
    }
  }

  getRoleLabel(role: string): string {
    const labels: { [key: string]: string } = {
      'ADMIN': 'Administrateur',
      'RH_MANAGER': 'Manager RH',
      'RH_STAFF': 'Staff RH',
      'READ_ONLY': 'Candidat'
    };
    return labels[role] || role;
  }

  formatDate(date: string): string {
    return new Date(date).toLocaleDateString('fr-FR');
  }

  openAddUserModal(): void {
    this.editingUser = null;
    this.formData = this.getEmptyForm();
    this.showModal = true;
  }

  editUser(user: User): void {
    this.editingUser = user;
    this.formData = { ...user, password: '' } as any;
    this.showModal = true;
  }

  saveUser(): void {
    if (!this.formData.full_name || !this.formData.email || !this.formData.username) {
      alert('Veuillez remplir tous les champs obligatoires');
      return;
    }

    if (this.editingUser) {
      // Update existing user
      this.userService.updateUser(this.editingUser.id, {
        full_name: this.formData.full_name,
        email: this.formData.email,
        username: this.formData.username,
        role: this.formData.role,
        is_active: this.formData.is_active
      }).subscribe({
        next: () => {
          this.closeModal();
          this.loadUsers();
        },
        error: (error) => {
          console.error('Error updating user:', error);
          alert('Erreur lors de la mise à jour de l\'utilisateur');
        }
      });
    } else {
      // Create new user
      if (!this.formData.password) {
        alert('Veuillez entrer un mot de passe pour le nouvel utilisateur');
        return;
      }

      this.userService.createUser(this.formData as UserCreate).subscribe({
        next: () => {
          this.closeModal();
          this.loadUsers();
        },
        error: (error) => {
          console.error('Error creating user:', error);
          alert('Erreur lors de la création de l\'utilisateur: ' + (error.error?.detail || 'Erreur inconnue'));
        }
      });
    }
  }

  deleteUser(user: User): void {
    if (confirm(`Êtes-vous sûr de vouloir supprimer ${user.full_name}?`)) {
      this.userService.deleteUser(user.id).subscribe({
        next: () => {
          this.loadUsers();
        },
        error: (error) => {
          console.error('Error deleting user:', error);
          alert('Erreur lors de la suppression de l\'utilisateur');
        }
      });
    }
  }

  closeModal(): void {
    this.showModal = false;
    this.editingUser = null;
    this.formData = this.getEmptyForm();
  }

  getEmptyForm() {
    return {
      full_name: '',
      email: '',
      username: '',
      role: 'READ_ONLY',
      password: '',
      is_active: true
    };
  }
}
