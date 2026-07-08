-- Add scoring fields to job_offers table
ALTER TABLE job_offers ADD COLUMN IF NOT EXISTS required_skills JSON DEFAULT NULL;
ALTER TABLE job_offers ADD COLUMN IF NOT EXISTS required_experience_years FLOAT DEFAULT NULL;
ALTER TABLE job_offers ADD COLUMN IF NOT EXISTS required_education_level VARCHAR(20) DEFAULT NULL;
ALTER TABLE job_offers ADD COLUMN IF NOT EXISTS weight_skills FLOAT NOT NULL DEFAULT 0.5;
ALTER TABLE job_offers ADD COLUMN IF NOT EXISTS weight_experience FLOAT NOT NULL DEFAULT 0.3;
ALTER TABLE job_offers ADD COLUMN IF NOT EXISTS weight_education FLOAT NOT NULL DEFAULT 0.2;

-- Create cv_analyses table
CREATE TABLE IF NOT EXISTS cv_analyses (
    id UUID PRIMARY KEY,
    application_id UUID NOT NULL UNIQUE,
    candidate_id UUID NOT NULL,
    raw_text TEXT,
    extracted_skills JSON NOT NULL DEFAULT '[]',
    extracted_experience_years FLOAT,
    extracted_education_level VARCHAR(20),
    extracted_job_titles JSON NOT NULL DEFAULT '[]',
    extracted_keywords JSON NOT NULL DEFAULT '[]',
    is_parsed BOOLEAN NOT NULL DEFAULT FALSE,
    parsed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_cv_analyses_application FOREIGN KEY (application_id) REFERENCES applications(id),
    CONSTRAINT fk_cv_analyses_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

CREATE INDEX IF NOT EXISTS ix_cv_analyses_application_id ON cv_analyses(application_id);
CREATE INDEX IF NOT EXISTS ix_cv_analyses_candidate_id ON cv_analyses(candidate_id);

-- Create candidate_scores table
CREATE TABLE IF NOT EXISTS candidate_scores (
    id UUID PRIMARY KEY,
    application_id UUID NOT NULL UNIQUE,
    job_offer_id UUID NOT NULL,
    candidate_id UUID NOT NULL,
    total_score FLOAT NOT NULL,
    skills_score FLOAT NOT NULL,
    experience_score FLOAT NOT NULL,
    education_score FLOAT NOT NULL,
    rank INTEGER,
    score_details JSON,
    computed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_candidate_scores_application FOREIGN KEY (application_id) REFERENCES applications(id),
    CONSTRAINT fk_candidate_scores_job_offer FOREIGN KEY (job_offer_id) REFERENCES job_offers(id),
    CONSTRAINT fk_candidate_scores_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

CREATE INDEX IF NOT EXISTS ix_candidate_scores_application_id ON candidate_scores(application_id);
CREATE INDEX IF NOT EXISTS ix_candidate_scores_job_offer_id ON candidate_scores(job_offer_id);
CREATE INDEX IF NOT EXISTS ix_candidate_scores_candidate_id ON candidate_scores(candidate_id);
CREATE INDEX IF NOT EXISTS ix_candidate_scores_job_rank ON candidate_scores(job_offer_id, rank);
