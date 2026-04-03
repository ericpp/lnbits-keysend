from lnbits.db import Connection


async def m001_initial(db: Connection):
    """
    Initial keysend table: addresses.
    """
    await db.execute(f"""
        CREATE TABLE keysend.entries (
            id TEXT PRIMARY KEY,
            wallet TEXT NOT NULL,
            description TEXT NOT NULL,
            username TEXT UNIQUE,
            custom_key TEXT NOT NULL,
            custom_value TEXT NOT NULL,
            domain TEXT,
            webhook_url TEXT,
            webhook_headers TEXT,
            webhook_body TEXT,
            created_at TIMESTAMP DEFAULT {db.timestamp_column_default},
            updated_at TIMESTAMP DEFAULT {db.timestamp_column_default},
            UNIQUE(custom_key, custom_value)
        );
    """)
