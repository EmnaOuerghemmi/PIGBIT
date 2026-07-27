import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { JobDetailComponent } from './job-detail.component';

/**
 * Parcours critique n°2 — candidature à une offre.
 *
 * C'est l'action qui fait vivre la plateforme : si le dépôt de CV casse,
 * plus aucune candidature n'entre. La validation du fichier est testée en
 * priorité car elle est la seule barrière côté client : un fichier refusé
 * par le serveur après téléversement, c'est plusieurs mégaoctets envoyés
 * pour rien et un message d'erreur tardif.
 */
describe('JobDetailComponent — candidature', () => {
  let component: JobDetailComponent;
  let fixture: ComponentFixture<JobDetailComponent>;
  let http: HttpTestingController;

  /** Fabrique un faux évènement de sélection de fichier. */
  function evenementFichier(nom: string, type: string, tailleOctets: number): Event {
    const fichier = new File(['x'], nom, { type });
    Object.defineProperty(fichier, 'size', { value: tailleOctets });
    return { target: { files: [fichier] } } as unknown as Event;
  }

  beforeEach(async () => {
    localStorage.clear();

    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
      imports: [JobDetailComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(JobDetailComponent);
    component = fixture.componentInstance;
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // ── Validation du fichier ────────────────────────────────────────────────

  it('accepte un PDF de taille raisonnable', () => {
    component.onFileSelected(evenementFichier('cv.pdf', 'application/pdf', 1024));

    expect(component.selectedFile).toBeTruthy();
    expect(component.errorMsg).toBe('');
  });

  it('refuse un format non autorise', () => {
    component.onFileSelected(evenementFichier('photo.png', 'image/png', 1024));

    expect(component.selectedFile).toBeNull();
    expect(component.errorMsg).toContain('PDF');
  });

  it('refuse un fichier de plus de 5 Mo', () => {
    const sixMo = 6 * 1024 * 1024;
    component.onFileSelected(evenementFichier('cv.pdf', 'application/pdf', sixMo));

    expect(component.selectedFile).toBeNull();
    expect(component.errorMsg).toContain('5 MB');
  });

  it('accepte un .docx dont le navigateur ne devine pas le type MIME', () => {
    // Certains navigateurs renvoient un type vide pour les .docx : la
    // validation doit alors se rabattre sur l'extension, sinon des CV
    // parfaitement valides sont rejetés.
    component.onFileSelected(evenementFichier('cv.docx', '', 2048));

    expect(component.selectedFile).toBeTruthy();
    expect(component.errorMsg).toBe('');
  });

  it('efface l erreur precedente apres une selection valide', () => {
    component.onFileSelected(evenementFichier('photo.png', 'image/png', 1024));
    expect(component.errorMsg).not.toBe('');

    component.onFileSelected(evenementFichier('cv.pdf', 'application/pdf', 1024));
    expect(component.errorMsg).toBe('');
  });

  // ── Envoi ────────────────────────────────────────────────────────────────

  it('n envoie rien sans fichier selectionne', () => {
    component.job = { id: 'job-1' } as any;
    component.selectedFile = null;

    component.apply();

    http.expectNone(r => r.url.includes('/apply/'));
    expect(component.isApplying).toBeFalse();
  });

  it('confirme la candidature apres une reponse positive', () => {
    component.job = { id: 'job-1' } as any;
    component.selectedFile = new File(['x'], 'cv.pdf', { type: 'application/pdf' });

    component.apply();
    expect(component.isApplying).toBeTrue();

    http.expectOne(r => r.url.includes('/apply/')).flush({ id: 'app-42' });

    expect(component.isApplying).toBeFalse();
    expect(component.successMsg).toContain('succès');
    // Le fichier est vidé pour éviter un double envoi par double clic.
    expect(component.selectedFile).toBeNull();
    expect(component.currentApplicationId).toBe('app-42');
  });

  it('signale une session expiree de maniere actionnable', () => {
    component.job = { id: 'job-1' } as any;
    component.selectedFile = new File(['x'], 'cv.pdf', { type: 'application/pdf' });

    component.apply();
    http.expectOne(r => r.url.includes('/apply/')).flush(
      { detail: 'Not authenticated' },
      { status: 401, statusText: 'Unauthorized' },
    );

    expect(component.isApplying).toBeFalse();
    expect(component.errorMsg).toContain('Reconnectez-vous');
  });

  it('distingue un serveur injoignable d une erreur applicative', () => {
    component.job = { id: 'job-1' } as any;
    component.selectedFile = new File(['x'], 'cv.pdf', { type: 'application/pdf' });

    component.apply();
    http.expectOne(r => r.url.includes('/apply/'))
        .error(new ProgressEvent('error'), { status: 0, statusText: 'Unknown Error' });

    expect(component.errorMsg).toContain('injoignable');
  });
});
