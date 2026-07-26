import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ScoreBreakdownComponent } from './score-breakdown.component';

describe('ScoreBreakdownComponent', () => {
  let component: ScoreBreakdownComponent;
  let fixture: ComponentFixture<ScoreBreakdownComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
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
