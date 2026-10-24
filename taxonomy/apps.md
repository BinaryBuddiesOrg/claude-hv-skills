# Apps taxonomy — stub

Same sections as `video.md`; to be filled when Phase 5 starts or by newadder.

## 1. Intents
landing page · dashboard · CRUD / admin tool · mobile app · desktop utility · API /
backend · browser extension · CLI tool · internal automation · MVP with auth + payments

## 2. Destinations
web (static host, Vercel/Netlify, Docker) · iOS / Android (Expo) · desktop (Tauri) ·
server (Docker, VPS) · package registry (npm, PyPI)

## 5. Style families (stacks)
`web-vite-react` · `web-next` · `mobile-expo` · `desktop-tauri` · `api-fastapi` ·
`api-node` · `cli-python` · `extension-chrome`

## 7. Question dimensions
platform · stack (Auto: from platform and what is installed) · auth (none, email,
OAuth) · data (none, local, hosted DB) · deploy target · design (plain, branded, use my
design system)

## 8. Auto decision table (seed)
"landing page" → static Vite + deploy to static host · "app with login" → Next + hosted
auth · "mobile" → Expo · always: tests + screenshots as the verify step

## 11. Gaps newadder should look at first
verify step per stack (what proves it runs: tests, Playwright screenshot, Lighthouse) ·
store-asset generation (screenshots in device frames) · scaffold version pinning
