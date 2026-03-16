CANONICAL_EXPOSURE_SCHEMA = {
    "required": [
        {"name": "lob", "type": "string", "example": "PROPERTY"},
        {"name": "peril", "type": "string", "example": "FLOOD"},
        {"name": "country", "type": "string", "example": "FR"},
        {"name": "tiv", "type": "number", "example": 1200000.0},
    ],
    "optional": [
        {"name": "region", "type": "string", "example": "IDF"},
        {"name": "city", "type": "string", "example": "Paris"},
        {"name": "premium", "type": "number", "example": 12000.0},
        {"name": "policy_id", "type": "string", "example": "POL-123"},
        {"name": "location_id", "type": "string", "example": "LOC-456"},
        {"name": "lat", "type": "number", "example": 48.8566},
        {"name": "lon", "type": "number", "example": 2.3522},
        {"name": "inception_date", "type": "date", "example": "2026-01-01"},
        {"name": "expiry_date", "type": "date", "example": "2026-12-31"},
        {"name": "sum_insured", "type": "number", "example": 500000.0},
        {"name": "limit", "type": "number", "example": 1000000.0},
        {"name": "deductible", "type": "number", "example": 25000.0},
    ],
    "enums": {
        "lob": ["PROPERTY", "ENERGY", "MARINE", "AVIATION", "CYBER", "LIABILITY", "POLITICAL_RISK"],
        "peril": ["FLOOD", "WIND", "QUAKE", "STORM", "FIRE", "TERROR"],
    },
    "notes": [
        "This schema is the normalized contract used by the platform and SDK.",
        "Ingestion mapping will map messy bordereau columns into this canonical schema.",
    ],
}