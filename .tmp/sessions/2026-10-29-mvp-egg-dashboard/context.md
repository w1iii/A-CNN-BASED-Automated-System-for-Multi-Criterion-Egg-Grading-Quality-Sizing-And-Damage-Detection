# Task Context: MVP Egg Inspection Dashboard

Session ID: 2026-10-29-mvp-egg-dashboard
Created: 2026-10-29
Status: in_progress

## Current Request
Rewrite the frontend to the supplied single-page live camera inspection dashboard.
Update API routes for the MVP. Remove authentication.

## Context Files (Standards to Follow)
- /Users/wii/.config/opencode/context/core/standards/code-quality.md
- /Users/wii/.config/opencode/context/ui/web/ui-styling-standards.md
- /Users/wii/.config/opencode/context/development/principles/api-design.md
- /Users/wii/.config/opencode/context/core/standards/security-patterns.md
- /Users/wii/.config/opencode/context/development/principles/clean-code.md
- /Users/wii/.config/opencode/context/core/workflows/component-planning.md

## Reference Files (Source Material to Look At)
- frontend/src/App.tsx
- frontend/src/api/client.ts
- frontend/src/types/index.ts
- frontend/src/pages/Upload.tsx
- frontend/src/components/upload/CameraCapture.tsx
- frontend/tailwind.config.js
- frontend/index.html
- backend/app/main.py
- backend/app/security.py
- backend/app/routers/predictions.py
- backend/app/routers/dashboard.py
- backend/app/routers/user_settings.py
- backend/app/schemas/__init__.py
- backend/app/services/prediction_service.py
- backend/app/models.py

## External Docs Fetched
None. No new packages. Existing React 18, Vite 5, Tailwind 3, FastAPI stack.

## Components
1. Backend auth-free operator context and route updates.
2. Frontend design tokens and shell.
3. Camera viewfinder with permission overlay and upload fallback.
4. Capture/analyze flow with real API.
5. Live result cards with real detection data and client-side crop thumbnails.
6. Status footer and batch export.

## Constraints
- Single-page MVP dashboard; no login/register/protected routes.
- Keep DB schema intact via one default local operator row; no migration.
- Match supplied visual design: Space Grotesk, JetBrains Mono, light glass panels, HUD corners.
- Existing tests must pass; update auth-specific tests where behavior changed.
- `npm run build` and backend tests must pass.

## Exit Criteria
- [ ] No auth router, JWT dependency, or login UI remains.
- [ ] All API endpoints work without auth using default operator.
- [ ] Dashboard captures/uploads image and renders real detection results.
- [ ] Frontend build passes.
- [ ] Backend tests pass.
