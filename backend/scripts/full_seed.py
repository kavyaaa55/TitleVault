"""
TitleVault — Full Seed Script
Pushes realistic sample data into every system layer via the live API:
  - 4 land parcels (2 admin, 2 user1)
  - 2 buildings per admin parcel
  - 2 flats per building
  - 1 LAND agreement + 1 FLAT agreement per parcel
  - Merkle root computed & anchored after all records
  - Verification of proofs
  - Analytics summary printed

Run from project root:
  python backend/scripts/full_seed.py
"""

import requests
import json
import sys
import time
from datetime import date, timedelta
from decimal import Decimal

BASE = "http://127.0.0.1:8000"

# ─────────────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────────────

def login(email: str, password: str) -> str:
    r = requests.post(f"{BASE}/auth/login", json={"username": email, "password": password})
    if r.status_code != 200:
        print(f"  ❌ Login failed for {email}: {r.status_code} {r.text}")
        sys.exit(1)
    token = r.json()["access_token"]
    print(f"  ✅ Logged in as {email}")
    return token

def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# ─────────────────────────────────────────────────────
# API wrappers
# ─────────────────────────────────────────────────────

def api(method: str, path: str, token: str, body: dict = None, label: str = "") -> dict:
    fn = getattr(requests, method)
    kwargs = {"headers": headers(token)}
    if body is not None:
        kwargs["json"] = body
    r = fn(f"{BASE}{path}", **kwargs)
    tag = label or path
    if r.status_code in (200, 201):
        print(f"  ✅ {method.upper()} {tag}  → {r.status_code}")
        return r.json()
    else:
        print(f"  ⚠️  {method.upper()} {tag}  → {r.status_code}  {r.text[:200]}")
        return {}

def api_no_auth(method: str, path: str, body: dict = None, label: str = "") -> dict:
    fn = getattr(requests, method)
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    r = fn(f"{BASE}{path}", **kwargs)
    tag = label or path
    if r.status_code in (200, 201):
        print(f"  ✅ {method.upper()} {tag}  → {r.status_code}")
        return r.json()
    else:
        print(f"  ⚠️  {method.upper()} {tag}  → {r.status_code}  {r.text[:200]}")
        return {}

# ─────────────────────────────────────────────────────
# Parcel geometry generators
# Each is a closed polygon [lng, lat] in India
# ─────────────────────────────────────────────────────

def polygon(base_lng: float, base_lat: float, size: float = 0.003) -> dict:
    """Generate a simple rectangular parcel polygon."""
    s = size
    coords = [
        [base_lng,       base_lat],
        [base_lng + s,   base_lat],
        [base_lng + s,   base_lat + s],
        [base_lng,       base_lat + s],
        [base_lng,       base_lat],   # closed
    ]
    return {"coordinates": coords}

# ─────────────────────────────────────────────────────
# Ethereum addresses (realistic but fake)
# ─────────────────────────────────────────────────────

ADDRESSES = {
    "admin":   "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
    "user1":   "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
    "buyer1":  "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
    "buyer2":  "0x90F79bf6EB2c4f870365E785982E1f101E93b906",
    "buyer3":  "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65",
    "buyer4":  "0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc",
    "tenant1": "0x976EA74026E726554dB657fA54763abd0C3a0aa9",
    "tenant2": "0x14dC79964da2C08b23698B3D3cc7Ca32193d9955",
}

# ─────────────────────────────────────────────────────
# Parcel definitions (not hardcoded values — built from params)
# ─────────────────────────────────────────────────────

def build_parcel(owner_key: str, survey: str, district: str, state: str,
                 land_type: str, area_sqft: float,
                 base_lng: float, base_lat: float,
                 owner_name: str, size: float = 0.003) -> dict:
    return {
        "owner_address": ADDRESSES[owner_key],
        "owner_name": owner_name,
        "survey_number": survey,
        "polygon": polygon(base_lng, base_lat, size),
        "metadata": {
            "district": district,
            "state": state,
            "land_type": land_type,
            "area_sqft": area_sqft,
            "usage": "residential",
            "registered_by": owner_key,
            "taluka": district,
            "village": f"{district} Village",
            "pincode": "400001",
        },
    }

PARCELS = [
    # ── Admin parcels ──────────────────────────────────
    build_parcel("admin", "MH-MU-001-2024",  "Mumbai",   "Maharashtra", "residential",  4500.0, 72.8777, 19.0760, "Rajesh Kumar Sharma",  0.0030),
    build_parcel("admin", "MH-PU-002-2024",  "Pune",     "Maharashtra", "commercial",   6200.0, 73.8567, 18.5204, "Priya Nair Iyer",       0.0025),
    # ── User1 parcels ──────────────────────────────────
    build_parcel("user1", "KA-BL-003-2024",  "Bangalore","Karnataka",   "agricultural", 8800.0, 77.5946, 12.9716, "Amit Singh Rathore",    0.0028),
    build_parcel("user1", "TN-CH-004-2024",  "Chennai",  "Tamil Nadu",  "residential",  3200.0, 80.2707, 13.0827, "Deepa Subramaniam",     0.0022),
]

# ─────────────────────────────────────────────────────
# Building definitions (built from parcel index)
# ─────────────────────────────────────────────────────

def build_building(land_hash: str, name: str, floors: int) -> dict:
    return {"land_record_hash": land_hash, "name": name, "total_floors": floors}

# ─────────────────────────────────────────────────────
# Flat definitions
# ─────────────────────────────────────────────────────

def build_flat(land_hash: str, building_id: str, flat_num: str,
               floor: str, owner_key: str, area: float) -> dict:
    return {
        "land_record_hash": land_hash,
        "building_id": building_id,
        "flat_number": flat_num,
        "floor_number": floor,
        "owner_address": ADDRESSES[owner_key],
        "area_m2": area,
        "is_transferable": True,
    }

# ─────────────────────────────────────────────────────
# Agreement builders
# ─────────────────────────────────────────────────────

def land_sale_agreement(record_hash: str, seller_key: str,
                        buyer_key: str, price: float) -> dict:
    today = date.today()
    return {
        "subject_type": "LAND",
        "subject_id": record_hash,
        "seller_address": ADDRESSES[seller_key],
        "buyer_address": ADDRESSES[buyer_key],
        "total_price": str(price),
        "paid_upfront": str(round(price * 0.20, 2)),
        "agreement_type": "SALE",
        "schedule": [
            {"amount": str(round(price * 0.30, 2)), "due_in_days": 30},
            {"amount": str(round(price * 0.30, 2)), "due_in_days": 60},
            {"amount": str(round(price * 0.20, 2)), "due_in_days": 90},
        ],
    }

def flat_lease_agreement(flat_id: str, owner_key: str,
                         tenant_key: str, monthly_rent: float) -> dict:
    annual = monthly_rent * 12
    end = date.today() + timedelta(days=365)
    return {
        "subject_type": "FLAT",
        "subject_id": flat_id,
        "seller_address": ADDRESSES[owner_key],
        "buyer_address": ADDRESSES[tenant_key],
        "total_price": str(annual),
        "paid_upfront": str(monthly_rent * 2),
        "agreement_type": "LEASE",
        "lease_end_date": end.isoformat(),
        "schedule": [
            {"amount": str(monthly_rent), "due_in_days": i * 30}
            for i in range(1, 11)
        ],
    }

# ─────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────

def main():
    print("\n" + "="*60)
    print("  TitleVault — Full Data Seed")
    print("="*60)

    # ── 1. Auth ───────────────────────────────────────
    print("\n[1/8] Authenticating...")
    admin_tok = login("admin@gmail.com", "admin@123")
    user1_tok = login("user1@gmail.com", "user1@123")

    # ── 2. Register Land Parcels ──────────────────────
    print("\n[2/8] Registering land parcels...")
    record_hashes = []
    record_ids = []
    for i, parcel in enumerate(PARCELS):
        owner = "admin" if i < 2 else "user1"
        tok = admin_tok  # only admin can create records
        result = api("post", "/registry/create", admin_tok, parcel,
                     label=f"register parcel #{i+1} ({parcel['metadata']['district']})")
        rh = result.get("record_hash", "")
        rid = result.get("id", "")
        record_hashes.append(rh)
        record_ids.append(rid)
        print(f"     hash={rh[:20]}...  id={rid[:8] if rid else 'n/a'}...")
        time.sleep(0.3)

    # ── 3. Buildings & Flats (admin parcels only) ─────
    print("\n[3/8] Registering buildings and flats (admin parcels)...")

    all_flat_ids = []     # [(flat_id, land_hash, owner_key)]
    all_building_ids = []

    building_specs = [
        # parcel 0 (Mumbai)
        [("Sunrise Heights Tower A", 12), ("Sunrise Heights Tower B", 8)],
        # parcel 1 (Pune)
        [("Prestige Commerce Park", 15), ("Prestige Annex Block", 6)],
    ]
    flat_specs = [
        # For each building: list of (flat_num, floor, owner_key, area_m2)
        [("101", "1st", "buyer1", 72.5), ("201", "2nd", "buyer2", 85.0)],
        [("102", "1st", "buyer3", 65.0), ("301", "3rd", "buyer4", 90.5)],
        [("A101", "1st", "buyer1", 110.0), ("B201", "2nd", "buyer2", 125.0)],
        [("A102", "1st", "tenant1", 95.0), ("B202", "2nd", "tenant2", 108.0)],
    ]

    flat_index = 0
    for parcel_idx in range(2):  # admin parcels
        rh = record_hashes[parcel_idx]
        if not rh:
            print(f"  ⚠️  Skipping buildings for parcel #{parcel_idx+1} (no hash)")
            flat_index += 2
            continue

        buildings_for_parcel = building_specs[parcel_idx]
        for b_idx, (bname, floors) in enumerate(buildings_for_parcel):
            bspec = build_building(rh, bname, floors)
            bres = api("post", "/building/create", admin_tok, bspec,
                       label=f"building '{bname}'")
            bid = bres.get("building_id", "")
            all_building_ids.append(bid)

            flats_for_building = flat_specs[flat_index]
            flat_index += 1
            for flat_num, floor, owner_key, area in flats_for_building:
                fspec = build_flat(rh, bid, flat_num, floor, owner_key, area)
                fres = api("post", "/flat/create", admin_tok, fspec,
                           label=f"flat {flat_num} in '{bname}'")
                fid = fres.get("flat_id", "")
                if fid:
                    all_flat_ids.append((fid, rh, owner_key))
                time.sleep(0.2)

    # ── 4. Land Agreements ────────────────────────────
    print("\n[4/8] Creating land sale agreements...")

    # admin parcel 0 → sale to buyer1
    agr_land_ids = []
    if record_hashes[0]:
        agr = land_sale_agreement(record_hashes[0], "admin", "buyer1", 15_000_000.0)
        res = api("post", "/agreement/create", admin_tok, agr,
                  label="land sale agreement (Mumbai)")
        aid = res.get("agreement_id", "")
        agr_land_ids.append(aid)

    # admin parcel 1 → sale to buyer2
    if record_hashes[1]:
        agr = land_sale_agreement(record_hashes[1], "admin", "buyer2", 22_000_000.0)
        res = api("post", "/agreement/create", admin_tok, agr,
                  label="land sale agreement (Pune)")
        aid = res.get("agreement_id", "")
        agr_land_ids.append(aid)

    # user1 parcel 0 → sale to buyer3
    if record_hashes[2]:
        agr = land_sale_agreement(record_hashes[2], "user1", "buyer3", 9_500_000.0)
        res = api("post", "/agreement/create", admin_tok, agr,
                  label="land sale agreement (Bangalore)")
        aid = res.get("agreement_id", "")
        agr_land_ids.append(aid)

    # user1 parcel 1 → sale to buyer4
    if record_hashes[3]:
        agr = land_sale_agreement(record_hashes[3], "user1", "buyer4", 7_800_000.0)
        res = api("post", "/agreement/create", admin_tok, agr,
                  label="land sale agreement (Chennai)")
        aid = res.get("agreement_id", "")
        agr_land_ids.append(aid)

    # ── 5. Flat Lease Agreements ──────────────────────
    print("\n[5/8] Creating flat lease agreements...")
    flat_lease_defs = [
        # (flat_id, owner_key, tenant_key, monthly_rent)
        (0, "admin",  "tenant1", 45_000.0),
        (1, "admin",  "tenant2", 52_000.0),
        (2, "buyer1", "tenant1", 38_000.0),
        (3, "buyer2", "tenant2", 60_000.0),
    ]
    agr_flat_ids = []
    for idx, owner_key, tenant_key, rent in flat_lease_defs:
        if idx >= len(all_flat_ids):
            break
        flat_id, land_hash, _ = all_flat_ids[idx]
        agr = flat_lease_agreement(flat_id, owner_key, tenant_key, rent)
        res = api("post", "/agreement/create", admin_tok, agr,
                  label=f"flat lease agreement (flat #{idx+1})")
        aid = res.get("agreement_id", "")
        agr_flat_ids.append(aid)
        time.sleep(0.2)

    # ── 6. Activate some agreements ───────────────────
    print("\n[6/8] Activating agreements...")
    all_agreement_ids = agr_land_ids + agr_flat_ids
    activated = []
    for aid in all_agreement_ids[:4]:   # activate first 4
        if not aid:
            continue
        res = api("post", f"/agreement/activate/{aid}", admin_tok,
                  label=f"activate agreement {aid[:8]}...")
        if res.get("status") == "ACTIVE":
            activated.append(aid)
        time.sleep(0.3)

    # Complete one land agreement (simulate completed sale)
    if activated:
        complete_id = activated[0]
        api("post", f"/agreement/action/complete/{complete_id}", admin_tok,
            label=f"complete agreement {complete_id[:8]}...")

    # ── 7. Merkle Anchoring ───────────────────────────
    print("\n[7/8] Computing and anchoring Merkle roots...")

    # Registry Merkle root
    root_res = api("get", "/registry/merkle/root", admin_tok,
                   label="GET registry merkle root")
    merkle_root = root_res.get("merkle_root", "")
    record_count = root_res.get("count", 0)
    print(f"     merkle_root={merkle_root[:20] if merkle_root else 'none'}...  records={record_count}")

    # Anchor the root on-chain
    anchor_res = api("post", "/registry/merkle/anchor", admin_tok,
                     label="POST anchor registry merkle root")
    print(f"     anchor result: {json.dumps(anchor_res)[:100]}")
    # Get Merkle proof for first valid record
    first_hash = next((h for h in record_hashes if h), None)
    if first_hash:
        proof_res = api("get", f"/registry/merkle/proof/{first_hash}", admin_tok,
                        label=f"GET merkle proof for record 1")
        proof_len = len(proof_res.get("proof", []))
        print(f"     proof length = {proof_len} nodes")

    # List merkle snapshots
    snaps_res = api("get", "/registry/merkle/snapshots", admin_tok,
                    label="GET merkle snapshots")
    snap_count = len(snaps_res) if isinstance(snaps_res, list) else snaps_res.get("count", "?")
    print(f"     snapshots = {snap_count}")

    # Agreement merkle
    agr_merkle = api("get", "/agreement/merkle/root", admin_tok,
                     label="GET agreement merkle root")
    print(f"     agreement merkle root: {str(agr_merkle)[:80]}")

    # ── 8. Verification & Analytics ───────────────────
    print("\n[8/8] Verification and analytics checks...")

    # Health
    api_no_auth("get", "/health/", label="GET /health")

    # Registry list
    list_res = api("get", "/registry/list?limit=20", admin_tok,
                   label="GET registry list")
    total = list_res.get("total", list_res.get("count", len(list_res.get("records", []))))
    print(f"     total records in DB = {total}")

    # Analytics summary (correct endpoint)
    analytics = api("get", "/analytics/agreements/summary", admin_tok,
                    label="GET analytics agreements summary")
    print(f"     analytics agreements: {json.dumps(analytics)[:120]}")

    land_analytics = api("get", "/analytics/land/summary", admin_tok,
                         label="GET analytics land summary")
    print(f"     analytics land: {json.dumps(land_analytics)[:120]}")

    # Explorer (public — by specific record)
    if record_hashes[0]:
        explorer = api_no_auth("get", f"/explorer/parcel/{record_hashes[0]}",
                               label="GET public explorer parcel #1")
        print(f"     public explorer parcel: {json.dumps(explorer)[:120]}")

    # Agreement list
    agr_list = api("get", "/agreement/list", admin_tok,
                   label="GET agreement list")
    agr_total = len(agr_list.get("items", []))
    print(f"     total agreements = {agr_total}")

    # Affidavit for first record (just check it doesn't error)
    first_id = next((i for i in record_ids if i), None)
    if first_id:
        aff_res = api("get", f"/registry/affidavit/{first_id}", admin_tok,
                      label=f"GET affidavit for record 1")
        print(f"     affidavit keys: {list(aff_res.keys()) if isinstance(aff_res, dict) else 'binary/pdf'}")

    # ── Summary ───────────────────────────────────────
    print("\n" + "="*60)
    print("  ✅ Seed Complete — Summary")
    print("="*60)
    print(f"  Land parcels registered : {sum(1 for h in record_hashes if h)}/4")
    print(f"  Buildings created       : {len(all_building_ids)}")
    print(f"  Flats created           : {len(all_flat_ids)}")
    print(f"  Agreements created      : {sum(1 for a in all_agreement_ids if a)}")
    print(f"  Agreements activated    : {len(activated)}")
    print(f"  Merkle root             : {merkle_root[:30] if merkle_root else '—'}...")
    print(f"  Records in DB           : {total}")
    print()
    print("  Open http://127.0.0.1:5173 to see the data.")
    print("  API docs: http://127.0.0.1:8000/docs")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
