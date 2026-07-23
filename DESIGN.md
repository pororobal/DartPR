# DartPR Design System

<!-- impeccable:design-schema 1 -->

## 1. Design Tokens

### Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-primary` | `#0B0C10` | Page background |
| `--bg-secondary` | `#14151A` | Secondary surfaces, sections |
| `--bg-card` | `#1A1B23` | Card/container backgrounds |
| `--bg-hover` | `#22232B` | Card hover state |
| `--text-primary` | `#E8E8ED` | Primary text, headings |
| `--text-secondary` | `#9498A3` | Body text, descriptions |
| `--text-muted` | `#5C5F6A` | Metadata, timestamps |
| `--accent-mint` | `#00E599` | Primary accent, CTAs, active states |
| `--accent-red` | `#F04452` | Negative signals, high risk |
| `--accent-blue` | `#3182F6` | Ticker symbols, links |
| `--accent-yellow` | `#F6C831` | Warning, medium signals |
| `--accent-purple` | `#8B5CF6` | Secondary accent |
| `--border-color` | `#2A2B33` | Card/container borders |
| `--shadow-card` | `0 4px 20px rgba(0,0,0,0.3)` | Card elevation |

### Typography

| Token | Value |
|-------|-------|
| Font UI | `Pretendard`, `-apple-system`, `BlinkMacSystemFont`, sans-serif |
| Font Mono | `JetBrains Mono`, monospace |
| Body | 14px/1.6, `--text-secondary` |
| Headings | Bold, `--text-primary` |
| Small/Tags | 10-11px, `--text-muted` |
| Ticker | 12px mono, `--accent-blue` |

### Spacing Scale

| Token | Value |
|-------|-------|
| Container max | 1200px (max-w-5xl = 1024px, max-w-3xl = 768px, max-w-7xl = 1280px) |
| Card padding | 16px (p-4) |
| Section padding | 80px vertical (py-20) |
| Gap (cards) | 16px (gap-4) / 24px (gap-6) |
| Border radius (cards) | 12px |
| Border radius (tags) | 4px |
| Border radius (buttons) | 8px |

## 2. Component Library

### Card (`.card`)
- Background: `--bg-card`
- Border: 1px solid `--border-color`
- Radius: 12px
- Transition: all 0.2s ease
- Hover: `--bg-hover` background, `--text-muted` border, shadow `--shadow-card`

### Button Primary (`.btn-primary`)
- Background: `--accent-mint`
- Text: `#0B0C10`
- Weight: 600
- Padding: 10px 24px
- Radius: 8px
- Hover: opacity 0.9, translateY(-1px)

### Button Outline (`.btn-outline`)
- Background: transparent
- Border: 1px solid `--accent-mint`
- Text: `--accent-mint`
- Weight: 600
- Padding: 10px 24px
- Radius: 8px

### Category Tag (`.category-tag`)
- Inline-flex with center alignment
- Padding: 2px 8px
- Radius: 4px
- Font: 11px, weight 600
- Per-category colors via `categoryColors` map

### Glass Effect (`.glass`)
- Background: `rgba(26, 27, 35, 0.8)`
- Backdrop-filter: blur(12px)
- Border: 1px solid `--border-color`

## 3. Typography Scale

| Level | Size | Weight | Color | Usage |
|-------|------|--------|-------|-------|
| H1 | 36-48px (responsive) | 700 | `--text-primary` | Page hero titles |
| H2 | 24px | 700 | `--text-primary` | Section headings |
| H3 | 16-18px | 700 | `--text-primary` | Card titles |
| Body | 14px | 400 | `--text-secondary` | Paragraphs, descriptions |
| Small | 12px | 400 | `--text-secondary` | Labels, secondary info |
| Micro | 10-11px | 400 | `--text-muted` | Tags, timestamps |
| Mono | 12px | 700 | `--accent-blue` | Ticker symbols |
| Score | 24px | 700 | varies | ScoreBadge |

## 4. Layout Rules

- Page max-width containers: `max-w-5xl mx-auto` (1024px) for content sections
- Navbar: fixed top, glass on scroll, height 64px
- Main content offset: `pt-16` (64px navbar)
- Feed layout: `max-w-3xl mx-auto` (768px) for live/history feeds
- Mobile: 16px padding (`px-4`)
- Grid: 1 col mobile, 3 col desktop for feature cards
- Cards in feed: full width, stacked vertically with 12px gap

## 5. Primitives

### DisclosureCard
- Layout: horizontal flex (content left, score right)
- Top row: ticker (mono blue) + category tag + risk tag + timestamp (right-aligned)
- Company name: 14px semibold, truncate
- Title: 12px secondary, 2-line clamp
- LLM Summary: 12px, italic, mint left border
- Score badge: fixed right side, 56x56 circular

### Navbar
- Logo: `DartPR` (mint `Dart` + white `PR`)
- Nav items: 14px medium weight, `--text-secondary`, hover → white
- Desktop: gap-8 between items
- Mobile: hidden (no hamburger yet)

## 6. States

| Component | Default | Hover | Active |
|-----------|---------|-------|--------|
| Card | bg-card + border | bg-hover + border-muted | - |
| btn-primary | mint bg | 0.9 opacity, -1px y | - |
| btn-outline | transparent + mint border | rgba(mint,0.1) bg | - |
| Nav link | text-secondary | text-white | - |
| ScoreBadge | per score color | - | - |

## 7. Motion

- Card: fadeInUp (0.3s, translateY(8px) → 0)
- Shimmer loading: gradient sweep 1.5s infinite
- btn-primary hover: translateY(-1px), 0.2s

## 8. Accessibility Constraints

- Dark theme reduces eye strain during extended sessions
- Color-coded scores (green/yellow/red) use both hue and position
- All interactive elements have visible hover states
- Font sizes meet 10px minimum for secondary content
- Accepting: no keyboard focus indicators yet, no ARIA labels on interactive elements
