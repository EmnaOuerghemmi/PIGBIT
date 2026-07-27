import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { AppComponent } from './app.component';

describe('AppComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
      imports: [AppComponent],
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it(`should have the 'frontend' title`, () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app.title).toEqual('frontend');
  });

  // L'assertion d'origine cherchait « Hello, frontend » dans un <h1> : le
  // template d'échafaudage d'Angular CLI, remplacé depuis par le
  // router-outlet. On vérifie désormais ce que la coquille rend réellement.
  it('should render the router outlet and the global overlays', () => {
    const fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;

    expect(compiled.querySelector('router-outlet')).toBeTruthy();
    // Toasts et boîte de confirmation doivent être disponibles quelle que
    // soit la route : les monter ailleurs les rendrait indisponibles hors
    // de la page qui les déclare.
    expect(compiled.querySelector('app-toast-container')).toBeTruthy();
    expect(compiled.querySelector('app-confirm-dialog')).toBeTruthy();
  });
});
