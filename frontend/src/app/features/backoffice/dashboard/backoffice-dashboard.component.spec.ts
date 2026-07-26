import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BackofficeDashboardComponent } from './backoffice-dashboard.component';

describe('BackofficeDashboardComponent', () => {
  let component: BackofficeDashboardComponent;
  let fixture: ComponentFixture<BackofficeDashboardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BackofficeDashboardComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(BackofficeDashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
