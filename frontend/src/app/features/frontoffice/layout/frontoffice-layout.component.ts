import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-frontoffice-layout',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './frontoffice-layout.component.html',
  styleUrls: ['./frontoffice-layout.component.css']
})
export class FrontofficeLayoutComponent implements OnInit {
  sidebarOpen = false;
  userName = '';
  userEmail = '';
  userInitial = '';

  constructor(private authService: AuthService, private router: Router) {}

  ngOnInit() {
    const user = this.authService.getCurrentUser();
    if (user) {
      this.userName = user.full_name || user.email;
      this.userEmail = user.email;
      this.userInitial = (user.full_name || user.email).charAt(0).toUpperCase();
    }
  }

  toggleSidebar() {
    this.sidebarOpen = !this.sidebarOpen;
  }

  closeSidebar() {
    this.sidebarOpen = false;
  }

  logout() {
    this.authService.logout();
  }
}
