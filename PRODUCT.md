# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Korean retail investors who monitor DART (전자공시시스템) disclosures for stock trading decisions. Primary user is an active trader who needs to process multiple disclosures quickly to identify market-moving events.

## Product Purpose

DartPR ingests real-time DART disclosures, scores them with a rules engine (DVI 0-100), and analyzes them with AI to help traders instantly assess whether a disclosure is bullish, bearish, or noise — without reading the full document.

## Positioning

Unlike generic DART search or raw disclosure feeds, DartPR quantifies every disclosure immediately with a DVI score and AI analysis, so traders never miss a material event or waste time on irrelevant filings.

## Operating Context

- Used alongside trading terminals and brokerage apps
- Disclosures arrive unpredictably throughout the trading day
- Speed matters — users need assessment within seconds of filing
- Mobile web and desktop, primarily Korean-language interface

## Capabilities and Constraints

- **Real-time feed**: Supabase Realtime pushes new disclosures to the browser instantly
- **DVI scoring**: Rule engine scores 0-100 on categories like financing, bio/pharma, earnings
- **AI analysis**: Groq/OpenAI LLM summarizes the disclosure, flags traps vs genuine catalysts
- **History**: Searchable/filterable past disclosures with scores and AI summaries
- **Pricing**: Free tier (3-min delay), Pro tier (real-time + API), Dev tier (API access)
- **Auth**: Supabase Auth with email/password
- **Backend**: Python FastAPI on Render
- **Frontend**: Next.js (Tailwind v4) on Vercel
- **Database**: Supabase Postgres
- Not yet available as a mobile app (web-only)

## Brand Commitments

- Name: DartPR (stylized as DartPR, not DART0s)
- Color: Mint accent (#00E599) on dark background (#0B0C10)
- Voice: Professional, direct, data-driven
- Font: Pretendard (UI), JetBrains Mono (code/data)

## Evidence on Hand

- Working prototype with real-time feed, history, pricing page
- Landing page with hero and feature sections
- DVI scoring for bio, financing, and earnings categories

## Product Principles

1. **Speed first**: Every millisecond matters — from disclosure arrival to score delivery
2. **Quantify everything**: Turn subjective disclosure reading into objective scores
3. **No noise**: Filter and rank so traders see only what matters
4. **Korean-first**: All UI, analysis, and content in Korean

## Accessibility & Inclusion

- Dark theme reduces eye strain during extended trading sessions
- Color-coded scores (green/yellow/red) for quick scanning
