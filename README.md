# partpilot
Project Repository of ITB Agentic AI Hackathon 2026

## Struktur Monorepo

Repositori ini disusun dengan struktur monorepo untuk memfasilitasi integrasi antarkomponen:
```text
partpilot/
├── docs/                  # Dokumentasi & panduan perancangan sistem
├── frontend-web/          # Dashboard frontend berbasis Next.js (App Router, Tailwind CSS, TypeScript)
├── pnpm-workspace.yaml    # Konfigurasi workspace pnpm
├── package.json           # Monorepo scripts (npm / pnpm)
└── README.md
```

## Memulai Frontend Web

### Menjalankan Development Server:
Dari root repositori:
```bash
npm run dev:web
# atau
pnpm --filter frontend-web dev
```

Atau langsung dari direktori `frontend-web`:
```bash
cd frontend-web
npm run dev
```

Buka [http://localhost:3000](http://localhost:3000) di browser.

### Build Production:
```bash
npm run build:web
```
