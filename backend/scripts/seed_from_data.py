"""
Seed a TitleVault Postgres database directly from backend/data/seed_data.json.

Unlike scripts/full_seed.py, this does NOT need the backend server, a blockchain
node, or IPFS running — it writes rows straight into the database using the same
models and canonical-hashing logic the live API uses, so the data looks the same
except there is no on-chain tx_hash / Merkle anchor.

Usage:
    cd backend
    pip install -r requirements.txt        # needs the backend's Python deps
    # point DATABASE_URL at the target Postgres (e.g. in backend/.env)
    alembic upgrade head                   # create the schema there first
    python scripts/seed_from_data.py       # [path/to/other_seed_data.json]
"""
import sys
import json
import bcrypt
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import (
    User, PropertyRecord, Building, FlatUnit, Agreement, AgreementStatus,
    SessionLocal,
)
from canonicalize import canonicalize_to_bytes, compute_keccak256_from_bytes
from utils.area import geodesic_area_m2
from shapely.geometry import Polygon

DATA_FILE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "data" / "seed_data.json"


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw[:72].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def local_cid(data: bytes) -> str:
    import hashlib
    return "Qm" + hashlib.sha256(data).hexdigest()[:44]


def rect_polygon(base_lng: float, base_lat: float, size: float):
    s = size
    return [
        [base_lng, base_lat],
        [base_lng + s, base_lat],
        [base_lng + s, base_lat + s],
        [base_lng, base_lat + s],
        [base_lng, base_lat],
    ]


def seed(data: dict):
    db = SessionLocal()
    addresses = data["addresses"]

    # ---------------- users ----------------
    for u in data["users"]:
        if db.query(User).filter(User.username == u["username"]).first():
            continue
        db.add(User(username=u["username"], password_hash=hash_password(u["password"]), roles=u["roles"]))
    db.commit()
    print(f"Users: {len(data['users'])} ensured")

    # ---------------- land parcels ----------------
    record_hash_by_key = {}
    for p in data["land_parcels"]:
        owner_address = addresses[p["owner_key"]]
        coords = rect_polygon(p["base_lng"], p["base_lat"], p["size"])

        canonical = {"owner": owner_address, "metadata": p["metadata"], "polygon": coords}
        canonical_bytes = canonicalize_to_bytes(canonical)
        record_hash_hex = compute_keccak256_from_bytes(canonical_bytes)
        record_hash_bytes = bytes.fromhex(record_hash_hex[2:])
        record_hash_by_key[p["key"]] = record_hash_hex

        existing = db.query(PropertyRecord).filter(PropertyRecord.record_hash == record_hash_bytes).first()
        if existing:
            continue

        area_m2 = geodesic_area_m2(Polygon(coords))

        db.add(PropertyRecord(
            cid=local_cid(canonical_bytes),
            record_hash=record_hash_bytes,
            canonical_hash=record_hash_bytes,
            format="CANONICAL",
            owner_address=owner_address,
            owner_name=p["owner_name"],
            survey_number=p["survey_number"],
            canonical_json=canonical_bytes.decode("utf-8"),
            geom={"type": "Polygon", "coordinates": [coords]},
            area_m2=area_m2,
        ))
    db.commit()
    print(f"Land parcels: {len(data['land_parcels'])} ensured")

    # ---------------- buildings + flats ----------------
    building_id_by_key = {}
    flat_id_by_ref = {}
    for b in data["buildings"]:
        land_hash_hex = record_hash_by_key[b["land_key"]]
        land_hash_bytes = bytes.fromhex(land_hash_hex[2:])

        building = db.query(Building).filter(
            Building.land_record_hash == land_hash_bytes, Building.name == b["name"]
        ).first()
        if not building:
            building = Building(land_record_hash=land_hash_bytes, name=b["name"], total_floors=b["total_floors"])
            db.add(building)
            db.commit()
            db.refresh(building)
        building_id_by_key[b["key"]] = building.id

        for f in b["flats"]:
            existing_flat = db.query(FlatUnit).filter(
                FlatUnit.building_id == building.id, FlatUnit.flat_number == f["flat_number"]
            ).first()
            if existing_flat:
                flat_id_by_ref[(b["key"], f["flat_number"])] = existing_flat.id
                continue

            canonical_flat = {
                "building_id": str(building.id),
                "land_record_hash": land_hash_hex,
                "flat_number": f["flat_number"],
                "floor_number": f["floor_number"],
                "area_m2": float(f["area_m2"]),
                "is_transferable": True,
            }
            flat_hash_hex = compute_keccak256_from_bytes(canonicalize_to_bytes(canonical_flat))

            flat = FlatUnit(
                flat_hash=bytes.fromhex(flat_hash_hex[2:]),
                building_id=building.id,
                land_record_hash=land_hash_bytes,
                flat_number=f["flat_number"],
                floor_number=f["floor_number"],
                owner_address=addresses[f["owner_key"]],
                area_m2=f["area_m2"],
                is_transferable=True,
                is_locked=False,
            )
            db.add(flat)
            db.commit()
            db.refresh(flat)
            flat_id_by_ref[(b["key"], f["flat_number"])] = flat.id
    print(f"Buildings: {len(data['buildings'])} ensured, flats ensured")

    # ---------------- agreements ----------------
    def make_agreement(subject_type, subject_id, seller_key, buyer_key, total_price,
                        agreement_type, schedule, lease_end=None):
        # Re-running the seed should not create a second agreement for the same
        # subject, regardless of what status the first one ended up in.
        existing = db.query(Agreement).filter(
            Agreement.subject_type == subject_type,
            Agreement.subject_id == subject_id,
        ).first()
        if existing:
            return existing

        canonical = {
            "subject_type": subject_type,
            "subject_id": subject_id,
            "buyer": addresses[buyer_key].lower(),
            "seller": addresses[seller_key].lower(),
            "total_price": int(total_price),
            "paid_upfront": int(schedule[0]["amount"]) if schedule else 0,
            "schedule": schedule,
            "agreement_type": agreement_type,
            "lease_end": lease_end,
        }
        canonical_bytes = canonicalize_to_bytes(canonical)
        agreement_hash = compute_keccak256_from_bytes(canonical_bytes)

        agreement = Agreement(
            subject_type=subject_type,
            subject_id=subject_id,
            canonical_json=canonical_bytes.decode("utf-8"),
            agreement_hash=bytes.fromhex(agreement_hash[2:]),
            status=AgreementStatus.DRAFT,
        )
        db.add(agreement)
        db.commit()
        db.refresh(agreement)
        return agreement

    count = 0
    for a in data["land_agreements"]:
        record_hash_hex = record_hash_by_key[a["land_key"]]
        price = a["total_price"]
        schedule = [
            {"amount": round(price * 0.20, 2), "due_in_days": 0},
            {"amount": round(price * 0.30, 2), "due_in_days": 30},
            {"amount": round(price * 0.30, 2), "due_in_days": 60},
            {"amount": round(price * 0.20, 2), "due_in_days": 90},
        ]
        agreement = make_agreement("LAND", record_hash_hex, a["seller_key"], a["buyer_key"], price, "SALE", schedule)
        count += 1

        if a.get("activate") and agreement.status == AgreementStatus.DRAFT:
            agreement.status = AgreementStatus.ACTIVE
            land = db.query(PropertyRecord).filter(PropertyRecord.record_hash == bytes.fromhex(record_hash_hex[2:])).first()
            land.is_transferable = False
            db.commit()
        if a.get("complete") and agreement.status == AgreementStatus.ACTIVE:
            agreement.status = AgreementStatus.COMPLETED
            db.commit()

    for a in data["flat_lease_agreements"]:
        flat_id = str(flat_id_by_ref[(a["building_key"], a["flat_number"])])
        rent = a["monthly_rent"]
        lease_end = (date.today() + timedelta(days=365)).isoformat()
        schedule = [{"amount": rent, "due_in_days": i * 30} for i in range(1, 11)]
        make_agreement("FLAT", flat_id, a["seller_key"], a["tenant_key"], rent * 12, "LEASE", schedule, lease_end)
        count += 1
    print(f"Agreements: {count} ensured")

    db.close()


if __name__ == "__main__":
    with open(DATA_FILE, "r", encoding="utf-8") as fh:
        seed(json.load(fh))
    print("Done.")
