import { Component, OnInit } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { GoogleService } from './core/services/google.service';
import { environment } from '../environments/environment';
import { ToastContainerComponent } from './shared/components/toast/toast-container.component';
import { ConfirmDialogComponent } from './shared/components/confirm-dialog/confirm-dialog.component';

@Component({
  selector: 'app-root',
  // Toasts et boîte de confirmation sont montés ici, une seule fois : ils
  // doivent rester disponibles quelle que soit la route affichée.
  imports: [RouterOutlet, ToastContainerComponent, ConfirmDialogComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent implements OnInit {
  title = 'frontend';

  constructor(private googleService: GoogleService) {}

  ngOnInit(): void {
    this.googleService.setClientId(environment.googleClientId);
  }
}
