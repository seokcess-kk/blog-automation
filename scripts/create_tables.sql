-- blog-automation Supabase 테이블 생성 스크립트
-- 실행: Supabase Dashboard > SQL Editor에서 실행

-- 1. keywords 테이블
CREATE TABLE IF NOT EXISTS keywords (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  keyword TEXT NOT NULL,
  blog_id TEXT NOT NULL,
  target_region TEXT,
  content_angle TEXT,
  status TEXT DEFAULT 'pending',
  schedule_date DATE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2. patterns 테이블
CREATE TABLE IF NOT EXISTS patterns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  keyword_id UUID REFERENCES keywords(id) ON DELETE CASCADE,
  keyword TEXT,
  source_urls TEXT[],
  avg_char_count INT,
  avg_image_count INT,
  avg_heading_count INT,
  title_patterns JSONB,
  keyword_placement JSONB,
  related_keywords TEXT[],
  content_structure JSONB,
  raw_data JSONB,
  analyzed_at TIMESTAMPTZ DEFAULT now()
);

-- 3. drafts 테이블
CREATE TABLE IF NOT EXISTS drafts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  keyword_id UUID REFERENCES keywords(id) ON DELETE CASCADE,
  pattern_id UUID REFERENCES patterns(id),
  title TEXT NOT NULL,
  body_html TEXT NOT NULL,
  tags TEXT[],
  meta_description TEXT,
  images JSONB,
  status TEXT DEFAULT 'draft',
  publish_at TIMESTAMPTZ,
  published_at TIMESTAMPTZ,
  naver_post_url TEXT,
  error_log TEXT,
  retry_count INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 4. publish_logs 테이블
CREATE TABLE IF NOT EXISTS publish_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  draft_id UUID REFERENCES drafts(id) ON DELETE CASCADE,
  blog_id TEXT NOT NULL,
  action TEXT NOT NULL,
  status TEXT NOT NULL,
  error_detail TEXT,
  duration_seconds FLOAT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_keywords_status ON keywords(status);
CREATE INDEX IF NOT EXISTS idx_keywords_blog_id ON keywords(blog_id);
CREATE INDEX IF NOT EXISTS idx_patterns_keyword_id ON patterns(keyword_id);
CREATE INDEX IF NOT EXISTS idx_drafts_status ON drafts(status);
CREATE INDEX IF NOT EXISTS idx_drafts_publish_at ON drafts(publish_at);
CREATE INDEX IF NOT EXISTS idx_publish_logs_draft_id ON publish_logs(draft_id);
CREATE INDEX IF NOT EXISTS idx_publish_logs_blog_id ON publish_logs(blog_id);

-- RLS (Row Level Security) 비활성화 (service_role 키 사용 시)
ALTER TABLE keywords ENABLE ROW LEVEL SECURITY;
ALTER TABLE patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE publish_logs ENABLE ROW LEVEL SECURITY;

-- service_role 전체 접근 정책
CREATE POLICY "Service role full access" ON keywords FOR ALL USING (true);
CREATE POLICY "Service role full access" ON patterns FOR ALL USING (true);
CREATE POLICY "Service role full access" ON drafts FOR ALL USING (true);
CREATE POLICY "Service role full access" ON publish_logs FOR ALL USING (true);

-- ============================================================
-- 브랜드 정보 기능 마이그레이션 (2026-03-12)
-- ============================================================

-- keywords 테이블에 브랜드 관련 컬럼 추가
ALTER TABLE keywords ADD COLUMN IF NOT EXISTS brand_url TEXT;
ALTER TABLE keywords ADD COLUMN IF NOT EXISTS brand_name TEXT;
ALTER TABLE keywords ADD COLUMN IF NOT EXISTS brand_info JSONB;

-- brand_info JSONB 구조 예시:
-- {
--   "crawled_at": "2026-03-12T10:00:00Z",
--   "main_page": { "title": "...", "text": "..." },
--   "sub_pages": [{ "url": "/about", "title": "...", "text": "..." }],
--   "extracted_strengths": ["강점1", "강점2"],
--   "extracted_services": ["서비스1", "서비스2"],
--   "brand_tone": "professional"
-- }

COMMENT ON COLUMN keywords.brand_url IS '브랜드 홈페이지 URL';
COMMENT ON COLUMN keywords.brand_name IS '브랜드명';
COMMENT ON COLUMN keywords.brand_info IS '크롤링된 브랜드 정보 (JSONB)';
