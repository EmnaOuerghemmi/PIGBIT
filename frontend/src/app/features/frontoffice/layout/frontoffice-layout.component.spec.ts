import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { FrontofficeLayoutComponent } from './frontoffice-layout.component';

describe('FrontofficeLayoutComponent', () => {
  let component: FrontofficeLayoutComponent;
  let fixture: ComponentFixture<FrontofficeLayoutComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
      imports: [FrontofficeLayoutComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(FrontofficeLayoutComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
