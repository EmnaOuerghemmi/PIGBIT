import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { CandidateRankingComponent } from './candidate-ranking.component';

describe('CandidateRankingComponent', () => {
  let component: CandidateRankingComponent;
  let fixture: ComponentFixture<CandidateRankingComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
      imports: [CandidateRankingComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(CandidateRankingComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
