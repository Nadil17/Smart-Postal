"""
Seed Data for Smart Locker Network - Colombo
============================================
8 Stations with 50-100 slots each
Total: ~600 locker slots across Colombo
"""

from datetime import datetime
import random

# Colombo Locker Stations with Real Addresses
COLOMBO_STATIONS = [
    {
        "id": "L01",
        "name": "Smart Locker - Fort Railway Station",
        "address": "Fort Railway Station, Olcott Mawatha, Colombo 01",
        "city": "Colombo",
        "latitude": 6.9344,
        "longitude": 79.8428,
        "operating_hours": "24/7",
        "contact_phone": "+94 11 2421281",
        "small_total": 30,
        "medium_total": 35,
        "large_total": 10,  # Total: 75 slots
    },
    {
        "id": "L02",
        "name": "Smart Locker - Pettah Central",
        "address": "Main Street, Pettah, Colombo 11",
        "city": "Colombo",
        "latitude": 6.9365,
        "longitude": 79.8500,
        "operating_hours": "6:00 AM - 10:00 PM",
        "contact_phone": "+94 11 2323456",
        "small_total": 25,
        "medium_total": 30,
        "large_total": 5,  # Total: 60 slots
    },
    {
        "id": "L03",
        "name": "Smart Locker - Havelock City Mall",
        "address": "Havelock City Mall, Havelock Road, Colombo 05",
        "city": "Colombo",
        "latitude": 6.8800,
        "longitude": 79.8700,
        "operating_hours": "8:00 AM - 10:00 PM",
        "contact_phone": "+94 11 2555123",
        "small_total": 35,
        "medium_total": 40,
        "large_total": 15,  # Total: 90 slots
    },
    {
        "id": "L04",
        "name": "Smart Locker - Nugegoda Super Market",
        "address": "High Level Road, Nugegoda",
        "city": "Nugegoda",
        "latitude": 6.8716,
        "longitude": 79.8916,
        "operating_hours": "7:00 AM - 9:00 PM",
        "contact_phone": "+94 11 2828100",
        "small_total": 20,
        "medium_total": 25,
        "large_total": 5,  # Total: 50 slots
    },
    {
        "id": "L05",
        "name": "Smart Locker - Wellawatte Junction",
        "address": "Galle Road, Wellawatte, Colombo 06",
        "city": "Colombo",
        "latitude": 6.8742,
        "longitude": 79.8612,
        "operating_hours": "24/7",
        "contact_phone": "+94 11 2363636",
        "small_total": 25,
        "medium_total": 30,
        "large_total": 10,  # Total: 65 slots
    },
    {
        "id": "L06",
        "name": "Smart Locker - Bambalapitiya Savoy",
        "address": "Galle Road, Bambalapitiya, Colombo 04",
        "city": "Colombo",
        "latitude": 6.8891,
        "longitude": 79.8558,
        "operating_hours": "24/7",
        "contact_phone": "+94 11 2508080",
        "small_total": 30,
        "medium_total": 35,
        "large_total": 15,  # Total: 80 slots
    },
    {
        "id": "L07",
        "name": "Smart Locker - Liberty Plaza",
        "address": "R.A. De Mel Mawatha, Colombo 03",
        "city": "Colombo",
        "latitude": 6.9147,
        "longitude": 79.8489,
        "operating_hours": "9:00 AM - 9:00 PM",
        "contact_phone": "+94 11 2575757",
        "small_total": 40,
        "medium_total": 45,
        "large_total": 15,  # Total: 100 slots
    },
    {
        "id": "L08",
        "name": "Smart Locker - Majestic City",
        "address": "Station Road, Bambalapitiya, Colombo 04",
        "city": "Colombo",
        "latitude": 6.8930,
        "longitude": 79.8530,
        "operating_hours": "10:00 AM - 10:00 PM",
        "contact_phone": "+94 11 2582582",
        "small_total": 35,
        "medium_total": 40,
        "large_total": 10,  # Total: 85 slots
    },
]


def generate_slot_id(station_id: str, size: str, number: int) -> str:
    """Generate unique slot ID: L01-S-001"""
    size_code = size[0].upper()  # S, M, or L
    return f"{station_id}-{size_code}-{number:03d}"


def generate_slots_for_station(station: dict) -> list:
    """Generate all slots for a station"""
    slots = []
    slot_num = 1
    
    # Calculate grid layout (10 columns max)
    max_columns = 10
    current_row = 1
    current_col = 1
    
    # Small slots
    for i in range(station["small_total"]):
        slots.append({
            "id": generate_slot_id(station["id"], "small", slot_num),
            "station_id": station["id"],
            "size": "small",
            "status": "available",
            "row": current_row,
            "column": current_col,
        })
        slot_num += 1
        current_col += 1
        if current_col > max_columns:
            current_col = 1
            current_row += 1
    
    # Medium slots (new row)
    current_row += 1
    current_col = 1
    for i in range(station["medium_total"]):
        slots.append({
            "id": generate_slot_id(station["id"], "medium", slot_num),
            "station_id": station["id"],
            "size": "medium",
            "status": "available",
            "row": current_row,
            "column": current_col,
        })
        slot_num += 1
        current_col += 1
        if current_col > max_columns:
            current_col = 1
            current_row += 1
    
    # Large slots (new row)
    current_row += 1
    current_col = 1
    for i in range(station["large_total"]):
        slots.append({
            "id": generate_slot_id(station["id"], "large", slot_num),
            "station_id": station["id"],
            "size": "large",
            "status": "available",
            "row": current_row,
            "column": current_col,
        })
        slot_num += 1
        current_col += 1
        if current_col > max_columns:
            current_col = 1
            current_row += 1
    
    return slots


def seed_lockers(db_session):
    """
    Seed the database with Colombo locker stations and slots
    """
    from models.locker import LockerStation, LockerSlot, SlotSize, SlotStatus
    
    print("🗄️ Seeding Smart Locker Network...")
    print("=" * 50)
    
    total_slots = 0
    
    for station_data in COLOMBO_STATIONS:
        # Check if station exists
        existing = db_session.query(LockerStation).filter_by(id=station_data["id"]).first()
        if existing:
            print(f"   ⏭️  Station {station_data['id']} already exists, skipping...")
            continue
        
        # Create station
        station = LockerStation(
            id=station_data["id"],
            name=station_data["name"],
            address=station_data["address"],
            city=station_data["city"],
            latitude=station_data["latitude"],
            longitude=station_data["longitude"],
            operating_hours=station_data["operating_hours"],
            contact_phone=station_data.get("contact_phone"),
            is_active=True,
            small_total=station_data["small_total"],
            medium_total=station_data["medium_total"],
            large_total=station_data["large_total"],
            total_slots=station_data["small_total"] + station_data["medium_total"] + station_data["large_total"],
            small_available=station_data["small_total"],
            medium_available=station_data["medium_total"],
            large_available=station_data["large_total"],
        )
        db_session.add(station)
        
        # Generate slots
        slots_data = generate_slots_for_station(station_data)
        for slot_data in slots_data:
            slot = LockerSlot(
                id=slot_data["id"],
                station_id=slot_data["station_id"],
                size=SlotSize(slot_data["size"]),
                status=SlotStatus.AVAILABLE,
                row=slot_data["row"],
                column=slot_data["column"],
            )
            db_session.add(slot)
        
        station_total = len(slots_data)
        total_slots += station_total
        print(f"   ✅ {station_data['name']}")
        print(f"      📍 {station_data['address']}")
        print(f"      🗄️  {station_total} slots (S:{station_data['small_total']}, M:{station_data['medium_total']}, L:{station_data['large_total']})")
    
    db_session.commit()
    
    print("=" * 50)
    print(f"✅ Seeded {len(COLOMBO_STATIONS)} stations with {total_slots} total slots")
    
    return {
        "stations": len(COLOMBO_STATIONS),
        "total_slots": total_slots
    }


def get_station_summary():
    """Print station summary without database"""
    print("\n🗄️ SMART LOCKER NETWORK - COLOMBO")
    print("=" * 60)
    
    total_slots = 0
    for station in COLOMBO_STATIONS:
        slots = station["small_total"] + station["medium_total"] + station["large_total"]
        total_slots += slots
        print(f"\n📍 {station['name']} ({station['id']})")
        print(f"   Address: {station['address']}")
        print(f"   Coords: ({station['latitude']}, {station['longitude']})")
        print(f"   Hours: {station['operating_hours']}")
        print(f"   Slots: {slots} (S:{station['small_total']}, M:{station['medium_total']}, L:{station['large_total']})")
    
    print("\n" + "=" * 60)
    print(f"📊 TOTAL: {len(COLOMBO_STATIONS)} Stations, {total_slots} Slots")
    print("=" * 60)


if __name__ == "__main__":
    get_station_summary()