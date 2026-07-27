import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { ScoreBreakdownComponent } from './score-breakdown.component';

describe('ScoreBreakdownComponent', () => {
  let component: ScoreBreakdownComponent;
  let fixture: ComponentFixture<ScoreBreakdownComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
      imports: [ScoreBreakdownComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(ScoreBreakdownComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
