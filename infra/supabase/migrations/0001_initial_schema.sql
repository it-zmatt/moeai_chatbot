-- ============================================================
-- ENUMS
-- ============================================================

CREATE TYPE tenant_plan AS ENUM ('free', 'starter', 'pro', 'enterprise');
CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system');
CREATE TYPE audit_operation AS ENUM ('INSERT', 'UPDATE', 'DELETE');


-- ============================================================
-- UTILITY: auto-update updated_at
-- ============================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- TENANTS
-- ============================================================

CREATE TABLE tenants (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name          text NOT NULL,
  slug          text NOT NULL UNIQUE,
  contact_email text NOT NULL,
  plan          tenant_plan NOT NULL DEFAULT 'free',
  is_active     boolean NOT NULL DEFAULT true,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_tenants_updated_at
  BEFORE UPDATE ON tenants
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_tenants_slug ON tenants (slug);


-- ============================================================
-- CLIENTS
-- ============================================================

CREATE TABLE clients (
  id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id               uuid NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
  name                    text NOT NULL,
  slug                    text NOT NULL UNIQUE,
  -- Array: supports multiple domains e.g. app.foo.com + www.foo.com
  allowed_domains         text[] NOT NULL DEFAULT '{}',
  system_prompt           text,
  widget_color            text,
  widget_greeting         text,
  -- LLM configuration: which provider/model this client is set up to use
  llm_provider            text NOT NULL DEFAULT 'openai'
                            CONSTRAINT valid_llm_provider CHECK (
                              llm_provider IN ('openai', 'anthropic', 'groq', 'mistral', 'gemini')
                            ),
  llm_model               text NOT NULL DEFAULT 'gpt-4o',
  rate_limit_per_session  integer NOT NULL DEFAULT 50,
  rate_limit_per_ip_hour  integer NOT NULL DEFAULT 100,
  is_active               boolean NOT NULL DEFAULT true,
  created_at              timestamptz NOT NULL DEFAULT now(),
  updated_at              timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_clients_updated_at
  BEFORE UPDATE ON clients
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_clients_tenant_id ON clients (tenant_id);
CREATE INDEX idx_clients_slug ON clients (slug);


-- ============================================================
-- API KEYS
-- ============================================================

CREATE TABLE api_keys (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id    uuid NOT NULL REFERENCES clients (id) ON DELETE CASCADE,
  -- Store only a secure hash (bcrypt / argon2) — never the raw key
  key_hash     text NOT NULL UNIQUE,
  label        text,
  is_active    boolean NOT NULL DEFAULT true,
  last_used_at timestamptz,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_api_keys_updated_at
  BEFORE UPDATE ON api_keys
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_api_keys_client_id ON api_keys (client_id);


-- ============================================================
-- CHAT SESSIONS
-- ============================================================

CREATE TABLE chat_sessions (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id            uuid NOT NULL REFERENCES clients (id) ON DELETE CASCADE,
  visitor_fingerprint  text,
  ip_address           inet,                  -- proper IP type for indexing/filtering
  message_count        integer NOT NULL DEFAULT 0,
  started_at           timestamptz NOT NULL DEFAULT now(),
  last_active_at       timestamptz NOT NULL DEFAULT now(),
  ended_at             timestamptz            -- null = session still open
);

CREATE INDEX idx_chat_sessions_client_id ON chat_sessions (client_id);
CREATE INDEX idx_chat_sessions_ip ON chat_sessions (ip_address);
CREATE INDEX idx_chat_sessions_fingerprint ON chat_sessions (visitor_fingerprint);


-- ============================================================
-- MESSAGES  (immutable — no updated_at by design)
-- ============================================================

CREATE TABLE messages (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id  uuid NOT NULL REFERENCES chat_sessions (id) ON DELETE CASCADE,
  role        message_role NOT NULL,
  content     text NOT NULL,
  api_provider text NOT NULL,           -- provider that answered this message e.g. 'anthropic'
  model_used   text NOT NULL,           -- exact model version e.g. 'claude-sonnet-4-20250514'
  tokens_used integer,
  latency_ms  integer,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- Prevent any UPDATE on messages — they are append-only
CREATE OR REPLACE FUNCTION prevent_message_update()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'messages are immutable and cannot be updated';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_messages_immutable
  BEFORE UPDATE ON messages
  FOR EACH ROW EXECUTE FUNCTION prevent_message_update();

CREATE INDEX idx_messages_session_id ON messages (session_id);
CREATE INDEX idx_messages_created_at ON messages (created_at);


-- ============================================================
-- USAGE EVENTS  (immutable — append-only billing record)
-- ============================================================

CREATE TABLE usage_events (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id     uuid NOT NULL REFERENCES clients (id) ON DELETE CASCADE,
  session_id    uuid REFERENCES chat_sessions (id) ON DELETE SET NULL,
  event_type    text NOT NULL,
  api_provider  text NOT NULL,           -- denormalized for fast billing queries
  model_used    text NOT NULL,           -- exact model version billed
  tokens_input  integer NOT NULL DEFAULT 0,
  tokens_output integer NOT NULL DEFAULT 0,
  cost_usd      numeric(10, 6) NOT NULL DEFAULT 0,  -- numeric > float for money
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION prevent_usage_event_update()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'usage_events are immutable and cannot be updated';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_usage_events_immutable
  BEFORE UPDATE ON usage_events
  FOR EACH ROW EXECUTE FUNCTION prevent_usage_event_update();

CREATE INDEX idx_usage_events_client_id ON usage_events (client_id);
CREATE INDEX idx_usage_events_session_id ON usage_events (session_id);
CREATE INDEX idx_usage_events_created_at ON usage_events (created_at);


-- ============================================================
-- AUDIT LOG  (covers tenants, clients, api_keys)
-- ============================================================

CREATE TABLE audit_logs (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  table_name   text NOT NULL,
  record_id    uuid NOT NULL,
  operation    audit_operation NOT NULL,
  old_data     jsonb,          -- full previous row snapshot
  new_data     jsonb,          -- full new row snapshot
  changed_by   uuid,           -- future: auth.users reference
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_logs_table_record ON audit_logs (table_name, record_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs (created_at);
-- GIN index for querying inside the JSON snapshots
CREATE INDEX idx_audit_logs_old_data ON audit_logs USING gin (old_data);
CREATE INDEX idx_audit_logs_new_data ON audit_logs USING gin (new_data);


-- Generic audit trigger function (reused across all audited tables)
CREATE OR REPLACE FUNCTION audit_record_change()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO audit_logs (table_name, record_id, operation, old_data, new_data)
  VALUES (
    TG_TABLE_NAME,
    CASE WHEN TG_OP = 'DELETE' THEN OLD.id ELSE NEW.id END,
    TG_OP::audit_operation,
    CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE to_jsonb(OLD) END,
    CASE WHEN TG_OP = 'DELETE' THEN NULL ELSE to_jsonb(NEW) END
  );
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Attach audit trigger to the three mutable config tables
CREATE TRIGGER trg_audit_tenants
  AFTER INSERT OR UPDATE OR DELETE ON tenants
  FOR EACH ROW EXECUTE FUNCTION audit_record_change();

CREATE TRIGGER trg_audit_clients
  AFTER INSERT OR UPDATE OR DELETE ON clients
  FOR EACH ROW EXECUTE FUNCTION audit_record_change();

CREATE TRIGGER trg_audit_api_keys
  AFTER INSERT OR UPDATE OR DELETE ON api_keys
  FOR EACH ROW EXECUTE FUNCTION audit_record_change();


-- ============================================================
-- ROW LEVEL SECURITY (Supabase)
-- Enable but keep permissive for now — tighten per-table later
-- ============================================================

ALTER TABLE tenants       ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients       ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys      ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages      ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_events  ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs    ENABLE ROW LEVEL SECURITY;