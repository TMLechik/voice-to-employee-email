PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS telegram_bot_clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id INTEGER NOT NULL UNIQUE,
    username TEXT,
    full_name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_telegram_bot_clients_username
    ON telegram_bot_clients (username);

CREATE TABLE IF NOT EXISTS message_recipients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_chat_id INTEGER NOT NULL UNIQUE,
    username TEXT,
    full_name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_message_recipients_username
    ON message_recipients (username);

CREATE TABLE IF NOT EXISTS client_recipient_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    recipient_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),

    CONSTRAINT fk_client_recipient_links_client
        FOREIGN KEY (client_id)
        REFERENCES telegram_bot_clients (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_client_recipient_links_recipient
        FOREIGN KEY (recipient_id)
        REFERENCES message_recipients (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_client_recipient_links_client_recipient
        UNIQUE (client_id, recipient_id)
);

CREATE INDEX IF NOT EXISTS idx_client_recipient_links_client_id
    ON client_recipient_links (client_id);

CREATE INDEX IF NOT EXISTS idx_client_recipient_links_recipient_id
    ON client_recipient_links (recipient_id);
