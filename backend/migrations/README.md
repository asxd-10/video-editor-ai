# Database Migrations

This directory contains the unified database schema.

## Directory Structure

```
migrations/
├── schema/                    # Unified schema files
│   ├── create_unified_schema.sql    # SQL schema definition
│   ├── create_schema.py             # Python script to create schema
│   └── README.md                   # Schema documentation
└── README.md                # This file
```

## Quick Start

To create the unified schema, see `schema/README.md` or run:

```bash
cd backend
python migrations/schema/create_schema.py
```

Or copy the SQL from `schema/create_unified_schema.sql` and run it in Supabase SQL Editor.
