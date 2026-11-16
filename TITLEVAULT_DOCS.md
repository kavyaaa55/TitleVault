# TitleVault — Complete Project Documentation

> A blockchain-backed property registry system for immutable land record management, legal agreements, and court-grade evidence generation.

---

## Table of Contents

1. [What Is TitleVault?](#1-what-is-titlevault)
2. [Architecture Overview](#2-architecture-overview)
3. [Tech Stack](#3-tech-stack)
4. [Smart Contracts](#4-smart-contracts)
5. [Backend (FastAPI)](#5-backend-fastapi)
6. [Frontend (React)](#6-frontend-react)
7. [Database Schema](#7-database-schema)
8. [Features — What You Can Do](#8-features--what-you-can-do)
9. [API Reference Summary](#9-api-reference-summary)
10. [Environment Variables](#10-environment-variables)
11. [Local Development Setup](#11-local-development-setup)
12. [Known Constraints (Local)](#12-known-constraints-local)
13. [Project Directory Map](#13-project-directory-map)

---

## 1. What Is TitleVault?

TitleVault is a **Government-grade blockchain property registry** system built to solve a core problem: land/property records get tampered with, lost, or disputed. TitleVault solves this by:

- Anchoring every property record as a **cryptographic hash on the Ethereum blockchain** — making records tamper-proof and immutable
- Storing full structured data in **PostgreSQL** (fast queries, relations)
- Storing canonical JSON blobs on **IPFS** (decentralized, content-addressed)
- Generating **legally-admissible PDF affidavits** with QR verification codes
- Producing **court evidence bundles** with Merkle inclusion proofs
- Supporting the full property hierarchy: **Land → Building → Flat**
- Managing **legal agreements** between parties (sale, lease, transfer) with on-chain anchoring
- Enabling **fraud detection** using ML anomaly scoring on ownership patterns

**Who uses it:**
| Role | What they do |
|------|-------------|
| **Admin** (Registrar) | Register properties, transfer ownership, create agreements, generate affidavits |
| **User** (Public/Owner) | View their properties, check status, download documents |
| **Court / Institution** | Use court bundle APIs to verify records independently |

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER BROWSER                             │
│                   React + TypeScript (Vite)                     │
│              Mapbox GL • Leaflet • shadcn/ui                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │  HTTP (REST)  port 5173
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                              │
│              Python 3.13 + Uvicorn  port 8000                   │
│   Routes • Models • Schemas • Merkle • Affidavits • GIS        │
└──────────┬────────────────┬───────────────────┬────────────────┘
           │                │                   │
           ▼                ▼                   ▼
  ┌─────────────┐  ┌──────────────┐   ┌────────────────┐
  │ PostgreSQL  │  │  Ethereum    │   │      IPFS      │
  │  port 5433  │  │  (Sepolia /  │   │   (optional,   │
  │  9 tables   │  │   Hardhat)   │   │   local mode)  │
  └─────────────┘  └──────────────┘   └────────────────┘
                          │
                   ┌──────────────┐
                   │  4 Solidity  │
                   │  Contracts   │
                   │  (Hardhat)   │
                   └──────────────┘
```

**Data Flow for a property record:**
1. Admin submits property form on frontend
2. Backend validates → creates canonical JSON → computes `keccak256` hash
3. Hash anchored on Ethereum via `RegistryResolver` smart contract
4. Canonical JSON uploaded to IPFS (CID stored in DB)
5. Record saved to PostgreSQL with on-chain tx hash
6. Merkle tree rebuilt → new root anchored on `RegistryRootAnchor`
7. PDF affidavit + QR code generated for download

---

## 3. Tech Stack

### 3.1 Frontend

| Technology | Version | Used For |
|-----------|---------|---------|
| **React** | 18 | UI framework |
| **TypeScript** | 5 | Type-safe frontend code |
| **Vite** | 5.4 | Build tool & dev server |
| **Bun** | latest | Package manager (faster than npm) |
| **Tailwind CSS** | 3 | Utility-first styling |
| **shadcn/ui** | — | Pre-built accessible UI components (Button, Card, Dialog, Table, etc.) |
| **Mapbox GL JS** | — | Interactive property parcel map with satellite/street views |
| **Leaflet** | — | Fallback map / GeoJSON polygon rendering |
| **Ethers.js** | 6 | Wallet connection & on-chain read calls from browser |
| **Recharts** | — | Analytics charts (ownership stats, agreement trends) |
| **React Router** | 6 | Client-side routing (SPA) |
| **React Query / fetch** | — | API calls to backend |

### 3.2 Backend

| Technology | Version | Used For |
|-----------|---------|---------|
| **Python** | 3.13 | Primary backend language |
| **FastAPI** | 0.104 | REST API framework with auto Swagger docs |
| **Uvicorn** | 0.24 | ASGI server |
| **SQLAlchemy** | 2.x | ORM — maps Python classes to PostgreSQL tables |
| **Alembic** | 1.13 | DB migration version control |
| **Pydantic** | 2.x | Request/response validation & serialization |
| **Web3.py** | 6.x | Python Ethereum client — sends txs, reads contract state |
| **eth-account** | — | ECDSA digital signing of records (Registrar key) |
| **bcrypt** | 4+ | Secure password hashing |
| **PyJWT** | — | JWT access + refresh token generation/validation |
| **slowapi** | 0.1.9 | Rate limiting (brute-force protection) |
| **ReportLab** | — | PDF generation for affidavits & court documents |
| **qrcode** | — | QR codes embedded in PDFs for offline verification |
| **Pillow** | — | Image processing for document rendering |
| **Shapely** | — | GIS geometry operations (intersection, area, overlap) |
| **pyproj** | — | Coordinate projection (lat/lng → metres for area calc) |
| **geojson** | — | GeoJSON format handling for parcel polygons |
| **scikit-learn** | — | ML fraud detection (anomaly scoring) |
| **numpy / pandas** | — | Numerical data analysis for fraud patterns |
| **merkletools** | — | Merkle tree construction + inclusion proof generation |
| **cryptography** | — | ECDSA signature generation for affidavits |
| **ipfshttpclient** | — | IPFS HTTP API client (content upload/fetch) |
| **psycopg2-binary** | — | PostgreSQL adapter |
| **Jinja2** | — | Template engine for legal document rendering |

### 3.3 Smart Contracts

| Technology | Used For |
|-----------|---------|
| **Solidity 0.8.20** | Smart contract language |
| **Hardhat** | Compile, test, deploy contracts |
| **OpenZeppelin** | Audited base contracts (AccessControl, Ownable) |
| **Ethers.js** | JavaScript interaction with contracts from scripts |
| **Ethereum Sepolia** | Public testnet for deployment |
| **Hardhat Network** | Local in-process blockchain for testing |

### 3.4 Database

| Technology | Used For |
|-----------|---------|
| **PostgreSQL 16** | Primary relational database |
| **Port 5433** | (non-default — this installation was set up this way) |
| **UUID primary keys** | All entity IDs are UUIDs for global uniqueness |

### 3.5 Infrastructure / Tooling

| Technology | Used For |
|-----------|---------|
| **Alchemy** | Hosted Ethereum node RPC (Sepolia testnet) |
| **Mapbox** | Map tiles, geocoding, satellite imagery |
| **Docker / docker-compose** | Container orchestration (for production / full deploy) |
| **IPFS** | Decentralized content-addressed document storage |

---

## 4. Smart Contracts

Located in `hardhat/contracts/`. Compiled artifacts (ABI + bytecode) go to `backend/contracts/abi/`.

### `RegistryResolver.sol`
**Purpose:** Core registry — stores the canonical hash of every property record on-chain.

| Function | What it does |
|---------|-------------|
| `registerRecord(bytes32 hash, string cid)` | Anchors a new property record hash + IPFS CID |
| `transferRecord(bytes32 oldHash, bytes32 newHash)` | Records an ownership transfer (new hash = new owner) |
| `getRecord(bytes32 hash)` | Returns on-chain metadata for a record |
| `recordExists(bytes32 hash)` | Returns true/false — used for verification |

**Access control:** Only the **Registrar address** (admin's Ethereum key) can call write functions.

---

### `RegistryRootAnchor.sol`
**Purpose:** Anchors Merkle tree roots on-chain for batch verification.

Each time a batch of records is processed, a Merkle root is computed from all record hashes and anchored here. Anyone can then verify any single record is in the batch with a Merkle inclusion proof (without needing the full dataset).

---

### `AgreementLedger.sol`
**Purpose:** Manages legal agreements (sale, lease, transfer) between parties.

| State | Meaning |
|-------|---------|
| `DRAFT` | Agreement created, not yet active |
| `ACTIVE` | Parties have confirmed, agreement in force |
| `COMPLETED` | Agreement fulfilled |
| `TERMINATED` | Agreement cancelled/breached |

---

### `AgreementMerkleAnchor.sol`
**Purpose:** Same as RegistryRootAnchor but specifically for agreement records. Allows court-verifiable batch proofs of agreement states.

---

## 5. Backend (FastAPI)

### Application Entry Point
`backend/app.py` — sets up FastAPI, CORS, rate limiter, registers all 35 route modules.

### Route Modules (`backend/routes/`)

| Route File | Prefix | What It Handles |
|-----------|--------|----------------|
| `auth_routes.py` | `/auth` | Login, register, token refresh |
| `registry_routes.py` | `/registry` | Create, list, transfer, verify property records |
| `subdivision_routes.py` | `/registry/subdivide` | Split a land parcel into child parcels |
| `building_routes.py` | `/building` | Register buildings under land parcels |
| `flat_routes.py` | `/flat` | Register flat units under buildings |
| `agreement_routes.py` | `/agreement` | Create and manage legal agreements |
| `agreement_enforcement_routes.py` | `/agreement` | Activate, complete, terminate agreements |
| `analytics_routes.py` | `/analytics` | Ownership stats, transfer trends, fraud scores |
| `explorer_routes.py` | `/explorer` | Public record browsing (no auth) |
| `heatmap_routes.py` | `/heatmap` | GIS heatmap data for map overlays |
| `map_routes.py` | `/map` | Parcel geometry for map rendering |
| `gis_appendix_routes.py` | `/gis` | GIS audit, area conservation checks |
| `gis_audit_routes.py` | `/gis/audit` | Spatial integrity enforcement |
| `registry_merkle_routes.py` | `/merkle` | Merkle root snapshots and inclusion proofs |
| `registry_affidavit_routes.py` | `/affidavit` | Generate PDF affidavits for property records |
| `agreement_affidavit_routes.py` | `/affidavit/agreement` | PDF affidavits for agreements |
| `flat_affidavit_routes.py` | `/affidavit/flat` | PDF affidavits for flat units |
| `court_bundle_routes.py` | `/court` | Package complete evidence bundles (ZIP) |
| `court_affidavit_routes.py` | `/court/affidavit` | Court-grade affidavit PDFs |
| `court_verification_routes.py` | `/court/verify` | Court-independent record verification |
| `pdf_verification_routes.py` | `/verify/pdf` | Verify a QR code / affidavit hash |
| `activity_routes.py` | `/activity` | User activity logs (real-time feed) |
| `admin_owner_routes.py` | `/admin` | Admin-only user management |
| `health_routes.py` | `/health` | Server health check |
| `subdivision_merkle_routes.py` | `/merkle/subdivision` | Merkle proofs for subdivisions |
| `agreement_merkle_routes.py` | `/merkle/agreement` | Merkle proofs for agreements |
| `pdf_batch_routes.py` | `/pdf/batch` | Batch PDF generation |

**Swagger UI:** `http://127.0.0.1:8000/docs` — interactive API explorer with 150+ endpoints.

### Key Backend Modules

| Module | Purpose |
|--------|---------|
| `web3_client.py` | Ethereum connection — sends transactions, reads contracts |
| `models.py` | SQLAlchemy ORM models (all 9 DB tables) |
| `canonical.py` | Deterministic JSON serialization for hash stability |
| `merkle/` | Merkle tree builder + proof generator |
| `affidavit/` | PDF generation engine using ReportLab |
| `indexer/registry_indexer.py` | Listens to blockchain events, syncs DB in real-time |
| `deps/auth.py` | JWT auth dependency — `get_current_user`, `require_admin` |
| `utils/area.py` | GIS area computation (pure-Python fallback for pyproj) |
| `fraud/` | ML fraud detection models |

---

## 6. Frontend (React)

### Pages (`frontend/src/pages/`)

| Page | Route | What It Shows |
|------|-------|--------------|
| `Home.tsx` | `/` | Landing page |
| `Auth.tsx` | `/auth` | Login / Register form |
| `Index.tsx` | `/registry` | Main dashboard (map + all features) |
| `StaticPages.tsx` | `/about`, `/privacy` | Static info pages |
| `NotFound.tsx` | `*` | 404 page |

### Key Components (`frontend/src/components/`)

| Component | Purpose |
|-----------|---------|
| `MapView` | Interactive Mapbox/Leaflet map with property parcels |
| `RegistryPanel` | Property list, search, filter |
| `CreatePropertyForm` | Admin form to register a new property |
| `TransferOwnershipForm` | Admin form to transfer ownership |
| `SubdivisionForm` | Admin form to subdivide a parcel |
| `BuildingForm` | Register a building under a land parcel |
| `FlatForm` | Register a flat under a building |
| `AgreementForm` | Create a legal agreement between parties |
| `MerkleProofViewer` | Display + verify a Merkle inclusion proof |
| `CourtBundlePanel` | Generate and download court evidence ZIP |
| `AnalyticsPanel` | Charts: ownership distribution, transfer history |
| `RealtimeStatusPanel` | Live feed of user activity |
| `AffidavitButton` | Download PDF affidavit for any record |

### Services (`frontend/src/services/`)

| Service | Purpose |
|---------|---------|
| `http.ts` | Base fetch wrapper — handles JWT auth headers, refresh |
| `registryApi.ts` | Calls to `/registry/*` endpoints |
| `adminApi.ts` | Calls to admin-only endpoints |

---

## 7. Database Schema

PostgreSQL database: `titlevault` (port 5433)

| Table | Purpose |
|-------|---------|
| `users` | Registered users — email, bcrypt password, role (admin/user) |
| `property_records` | Land parcels — owner, geometry (GeoJSON), hash, IPFS CID, tx hash |
| `buildings` | Buildings under a land parcel — floors, type, etc. |
| `flat_units` | Individual flats inside buildings |
| `agreements` | Legal agreements — parties, type, value, status lifecycle |
| `agreement_installments` | Payment schedule rows linked to an agreement |
| `audit_logs` | Every action logged — who did what, when, what hash |
| `merkle_snapshots` | Merkle root snapshots — root hash, block number, timestamp |
| `refresh_tokens` | Active JWT refresh tokens (7-day expiry) |

---

## 8. Features — What You Can Do

### As Admin (`admin@gmail.com` / `admin@123`)

#### Property Registry
- **Register a property** — submit parcel geometry (draw on map or paste GeoJSON), owner details, survey number. Gets hashed and anchored on-chain.
- **Transfer ownership** — change the owner of a parcel. Creates a new immutable record linked to the old one (no data is ever deleted).
- **Subdivide a parcel** — split one parcel into N child parcels. The system enforces ≥99% area conservation.
- **View full lineage** — see the entire ownership history of any parcel going back to registration.

#### Vertical Ownership (Buildings & Flats)
- **Register a building** under a land parcel (address, floors, type)
- **Register flat units** under a building (unit number, area, floor)
- Each flat gets its own record, hash, and affidavit

#### Legal Agreements
- **Create an agreement** — link two parties (buyer/seller or landlord/tenant) to a subject (land/building/flat)
- **Set installments** — define a payment schedule
- **Lifecycle management** — move agreements: DRAFT → ACTIVE → COMPLETED or TERMINATED
- Agreements are **anchored on-chain** via `AgreementLedger`

#### Cryptographic Verification & Documents
- **Generate PDF affidavit** for any record — includes digital registrar signature + QR code
- **Merkle proof** — prove any record is in the registry without revealing others
- **Court evidence bundle** — download a ZIP with: canonical JSON + affidavit PDF + Merkle proof + GIS appendix
- **Verify any affidavit** — QR scan or hash lookup confirms integrity

#### Analytics & GIS
- **Ownership heatmap** — visual density of registered properties
- **Transfer heatmap** — where transactions are happening
- **Agreement heatmap** — agreement concentration map
- **Fraud detection scores** — ML anomaly scores for suspicious patterns
- **Spatial audit** — verify area conservation after subdivisions

### As User (`user1@gmail.com` / `user1@123`)
- Browse public registry (no auth required at `/explorer`)
- View their own property records
- Download affidavits
- View activity feed

### Public (No Login)
- `GET /explorer/list` — browse all records
- `GET /registry/verify/{hash}` — verify any record hash on-chain
- `GET /health` — server health check
- `GET /docs` — full Swagger API documentation

---

## 9. API Reference Summary

Base URL: `http://127.0.0.1:8000`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/login` | No | Login → returns JWT tokens |
| POST | `/auth/register` | Admin | Create a new user |
| POST | `/auth/refresh` | No | Refresh access token |
| GET | `/registry/list` | No | List all property records |
| POST | `/registry/create` | Admin | Register a new property |
| POST | `/registry/transfer` | Admin | Transfer ownership |
| GET | `/registry/verify/{hash}` | No | Verify record on-chain |
| POST | `/registry/subdivide` | Admin | Subdivide a parcel |
| POST | `/building/create` | Admin | Register a building |
| POST | `/flat/create` | Admin | Register a flat |
| POST | `/agreement/create` | Admin | Create an agreement |
| POST | `/agreement/activate/{id}` | Admin | Activate an agreement |
| POST | `/agreement/action/{action}/{id}` | Admin | Complete/terminate |
| GET | `/merkle/proof/{hash}` | No | Get Merkle inclusion proof |
| GET | `/affidavit/{record_id}` | Auth | Download PDF affidavit |
| GET | `/court/bundle/{subject_id}` | Admin | Download court evidence ZIP |
| GET | `/analytics/summary` | Auth | Ownership analytics |
| GET | `/heatmap/ownership` | No | Ownership heatmap data |
| GET | `/explorer/list` | No | Public record browser |
| GET | `/activity/my-activity` | Auth | Current user's activity log |
| GET | `/health` | No | Server health check |
| GET | `/docs` | No | Swagger UI |

---

## 10. Environment Variables

### `backend/.env`

| Variable | Value | Purpose |
|----------|-------|---------|
| `DATABASE_URL` | `postgresql+psycopg2://postgres:postgres@localhost:5433/titlevault` | PostgreSQL connection |
| `WEB3_PROVIDER` | Alchemy Sepolia URL | Ethereum RPC endpoint |
| `ALCHEMY_HTTP` | Alchemy Sepolia URL | Same — for indexer |
| `DISABLE_ONCHAIN` | `true` | Skip on-chain writes (local mode) |
| `REGISTRAR_PRIVATE_KEY` | Hardhat account #1 key | Signs transactions & affidavits |
| `REGISTRAR_ADDRESS` | Hardhat account #1 address | On-chain authority address |
| `CONTRACT_ADDRESS` | RegistryResolver address | Main registry contract |
| `REGISTRY_ROOT_CONTRACT` | RegistryRootAnchor address | Merkle root contract |
| `AGREEMENT_LEDGER_ADDRESS` | AgreementLedger address | Agreement contract |
| `AGREEMENT_MERKLE_ANCHOR_ADDRESS` | AgreementMerkleAnchor address | Agreement Merkle contract |
| `SECRET_KEY` | 64-char hex string | JWT signing secret |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `IPFS_PROVIDER` | `local` | Use local IPFS or mock |
| `PUBLIC_BASE_URL` | `http://127.0.0.1:8000` | Used in QR codes / affidavits |

### `frontend/.env`

| Variable | Value | Purpose |
|----------|-------|---------|
| `VITE_API_BASE` | `http://localhost:8000` | Backend API URL (used by http.ts) |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Same (legacy var) |
| `VITE_CHAIN_ID` | `11155111` | Ethereum Sepolia chain ID |
| `VITE_RPC_URL` | Alchemy Sepolia URL | Blockchain RPC from browser |
| `VITE_REGISTRY_CONTRACT` | RegistryResolver address | Contract to interact with |
| `VITE_AGREEMENT_CONTRACT` | AgreementLedger address | Agreement contract |
| `VITE_MAPBOX_TOKEN` | Your Mapbox public token | Map tiles & geocoding |

---

## 11. Local Development Setup

### Prerequisites
- **Node.js** 18+ and **Bun** (frontend)
- **Python** 3.11+ (backend)
- **PostgreSQL 16** (database)
- **Alchemy account** (Sepolia RPC)
- **Mapbox account** (map tiles)

### Start Order (every session)

**Step 1 — Start PostgreSQL** (run once, keep running)
```powershell
& "C:\Program Files\PostgreSQL\16\bin\postgres.exe" -D "C:\Program Files\PostgreSQL\16\data"
# Runs on port 5433
```

**Step 2 — Start Backend**
```powershell
cd D:\coding\Blockchain_CP\TitleVault\backend
.\venv\Scripts\uvicorn.exe app:app --host 127.0.0.1 --port 8000
# API at http://127.0.0.1:8000
# Docs at http://127.0.0.1:8000/docs
```

**Step 3 — Start Frontend**
```powershell
cd D:\coding\Blockchain_CP\TitleVault\frontend
bun run dev
# App at http://127.0.0.1:5173
```

### Demo Users
| Email | Password | Role |
|-------|----------|------|
| `admin@gmail.com` | `admin@123` | Admin (full access) |
| `user1@gmail.com` | `user1@123` | User (read + own records) |

---

## 12. Known Constraints (Local)

| Constraint | Reason | Workaround |
|------------|--------|-----------|
| `DISABLE_ONCHAIN=true` | Windows Application Control blocks `.node` EDR file — Hardhat node can't run persistently | Records stored in DB only; no live blockchain writes |
| Alchemy used as RPC | Same reason — can't run local `hardhat node` persistently | Using Sepolia testnet via Alchemy for reads |
| Some `.pyd` files disabled | Windows blocks unsigned Cython DLLs on D: drive | Pure-Python fallbacks written for SQLAlchemy, pyproj, bitarray |
| IPFS not running | No local IPFS daemon started | `IPFS_PROVIDER=local` mocks storage; affidavits still generate |
| PostgreSQL on port 5433 | Existing data directory was configured this way | All `.env` files point to 5433 |
| passlib broken with bcrypt 5+ | `__about__` attribute removed in bcrypt 5.x | Replaced with direct `import bcrypt` in auth_routes.py |

---

## 13. Project Directory Map

```
TitleVault/
├── TITLEVAULT_DOCS.md          <- This file
├── README.md                   <- Original project README
├── docker-compose.yml          <- Full-stack Docker orchestration
├── LICENSE
│
├── hardhat/                    <- Blockchain / Smart Contracts
│   ├── contracts/
│   │   ├── RegistryResolver.sol
│   │   ├── RegistryRootAnchor.sol
│   │   ├── AgreementLedger.sol
│   │   └── AgreementMerkleAnchor.sol
│   ├── scripts/                <- Deployment scripts
│   ├── test/                   <- Contract unit tests
│   ├── hardhat.config.js
│   └── package.json
│
├── backend/                    <- Python FastAPI Application
│   ├── app.py                  <- Main application entry point
│   ├── models.py               <- SQLAlchemy DB models
│   ├── web3_client.py          <- Ethereum connection layer
│   ├── canonical.py            <- Deterministic JSON / hash logic
│   ├── routes/                 <- 35 route modules (all API endpoints)
│   ├── schemas/                <- Pydantic request/response models
│   ├── deps/                   <- FastAPI dependencies (auth, DB session)
│   ├── merkle/                 <- Merkle tree construction & proofs
│   ├── affidavit/              <- PDF generation engine
│   ├── indexer/                <- Blockchain event listener/syncer
│   ├── fraud/                  <- ML fraud detection
│   ├── utils/                  <- Helpers (area calc, GIS, etc.)
│   ├── contracts/abi/          <- Compiled contract ABIs (from Hardhat)
│   ├── alembic/                <- DB migration files
│   ├── scripts/                <- Utility scripts (seed_db.py, etc.)
│   ├── requirements.txt
│   └── .env                    <- Backend environment variables
│
├── frontend/                   <- React TypeScript Application
│   ├── src/
│   │   ├── pages/              <- Route-level page components
│   │   ├── components/         <- Reusable UI components
│   │   ├── services/           <- API client (http.ts, registryApi.ts)
│   │   ├── hooks/              <- React hooks (realtime, auth, map)
│   │   ├── lib/                <- Utilities
│   │   ├── types/              <- TypeScript type definitions
│   │   └── App.tsx             <- Router setup
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── .env                    <- Frontend environment variables
│
└── .kiro/                      <- Project specification & steering docs
    ├── docs/                   <- Implementation summaries
    ├── specs/                  <- Feature requirements
    └── steering/               <- Architecture guidelines per domain
```

---

> **TitleVault** was designed as a production-grade institutional system — 15 development phases covering everything from core registry to court-admissible evidence, GIS spatial enforcement, ML fraud detection, and long-term archival. The local setup uses `DISABLE_ONCHAIN=true` to skip live blockchain writes; for full blockchain anchoring, deploy contracts to Sepolia using Alchemy.
