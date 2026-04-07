-- Test seed data (deterministic UUIDs for fixtures).
-- Run after migrations. `supabase db reset` applies migrations then this file.

-- ---------------------------------------------------------------------------
-- Tenants
-- ---------------------------------------------------------------------------
INSERT INTO tenants (id, name, slug, contact_email, plan, is_active)
VALUES
  (
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1',
    'Acme Corporation',
    'acme',
    'ops@acme.example',
    'pro',
    true
  ),
  (
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1',
    'Beta Labs',
    'beta-labs',
    'hello@betalabs.example',
    'starter',
    true
  );

-- ---------------------------------------------------------------------------
-- Clients
-- ---------------------------------------------------------------------------
INSERT INTO clients (
  id,
  tenant_id,
  name,
  slug,
  allowed_domains,
  system_prompt,
  widget_color,
  widget_greeting,
  llm_provider,
  llm_model,
  rate_limit_per_session,
  rate_limit_per_ip_hour,
  is_active
)
VALUES
  (
    'cccccccc-cccc-cccc-cccc-ccccccccccc1',
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1',
    'Acme Marketing Widget',
    'acme-marketing',
    ARRAY['marketing.acme.example', 'www.acme.example'],
    'You are a helpful assistant for Acme marketing site visitors. Be concise.',
    '#2563eb',
    'Hi! Ask us anything about Acme products.',
    'openai',
    'gpt-4o',
    80,
    200,
    true
  ),
  (
    'cccccccc-cccc-cccc-cccc-ccccccccccc2',
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1',
    'Acme Support Portal',
    'acme-support',
    ARRAY['support.acme.example'],
    'You are Acme tier-1 support. Escalate billing to a human.',
    '#059669',
    'Welcome to Acme support. How can we help?',
    'anthropic',
    'claude-sonnet-4-20250514',
    50,
    100,
    true
  ),
  (
    'cccccccc-cccc-cccc-cccc-ccccccccccc3',
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1',
    'Beta Labs App',
    'beta-app',
    ARRAY['app.betalabs.example', 'localhost'],
    'You are the in-app guide for Beta Labs SaaS.',
    '#7c3aed',
    'Hey there — need a hand with Beta?',
    'groq',
    'llama-3.3-70b-versatile',
    40,
    80,
    true
  );

-- ---------------------------------------------------------------------------
-- API keys (hashes are fake bcrypt-shaped strings — replace in real tests)
-- ---------------------------------------------------------------------------
INSERT INTO api_keys (id, client_id, key_hash, label, is_active, last_used_at)
VALUES
  (
    'dddddddd-dddd-dddd-dddd-ddddddddddd1',
    'cccccccc-cccc-cccc-cccc-ccccccccccc1',
    '$2b$12$abcdefghijklmnopqrstuvABCDEFGHIJKLMNOPQRSTUV', -- not a real hash
    'Staging embed key',
    true,
    now() - interval '2 hours'
  ),
  (
    'dddddddd-dddd-dddd-dddd-ddddddddddd2',
    'cccccccc-cccc-cccc-cccc-ccccccccccc1',
    '$2b$12$zyxwvutsrqponmlkjihgfedcbaZYXWVUTSRQPONMLKJIHGF', -- not a real hash
    'CI test key',
    true,
    NULL
  ),
  (
    'dddddddd-dddd-dddd-dddd-ddddddddddd3',
    'cccccccc-cccc-cccc-cccc-ccccccccccc2',
    '$2b$12$0123456789abcdef0123456789abcdef0123456789abcd', -- not a real hash
    'Production support',
    true,
    now() - interval '1 day'
  ),
  (
    'dddddddd-dddd-dddd-dddd-ddddddddddd4',
    'cccccccc-cccc-cccc-cccc-ccccccccccc3',
    '$2b$12$FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF', -- not a real hash
    'Local dev',
    true,
    now() - interval '5 minutes'
  );

-- ---------------------------------------------------------------------------
-- Chat sessions
-- ---------------------------------------------------------------------------
INSERT INTO chat_sessions (
  id,
  client_id,
  visitor_fingerprint,
  ip_address,
  message_count,
  started_at,
  last_active_at,
  ended_at
)
VALUES
  (
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee1',
    'cccccccc-cccc-cccc-cccc-ccccccccccc1',
    'fp_acme_visitor_001',
    '203.0.113.10'::inet,
    4,
    now() - interval '3 days',
    now() - interval '3 days' + interval '12 minutes',
    now() - interval '3 days' + interval '15 minutes'
  ),
  (
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee2',
    'cccccccc-cccc-cccc-cccc-ccccccccccc1',
    'fp_acme_visitor_002',
    '198.51.100.22'::inet,
    0,
    now() - interval '1 hour',
    now() - interval '1 hour',
    NULL
  ),
  (
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee3',
    'cccccccc-cccc-cccc-cccc-ccccccccccc2',
    'fp_support_ticket_99',
    '192.0.2.5'::inet,
    6,
    now() - interval '6 hours',
    now() - interval '6 hours' + interval '25 minutes',
    NULL
  ),
  (
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee4',
    'cccccccc-cccc-cccc-cccc-ccccccccccc3',
    'fp_beta_user_alpha',
    '127.0.0.1'::inet,
    2,
    now() - interval '30 minutes',
    now() - interval '28 minutes',
    NULL
  );

-- ---------------------------------------------------------------------------
-- Messages (append-only)
-- ---------------------------------------------------------------------------
INSERT INTO messages (
  id,
  session_id,
  role,
  content,
  api_provider,
  model_used,
  tokens_used,
  latency_ms,
  created_at
)
VALUES
  (
    'ffffffff-ffff-ffff-ffff-ffffffffff01',
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee1',
    'user',
    'What plans do you offer for small teams?',
    'openai',
    'gpt-4o',
    18,
    NULL,
    now() - interval '3 days' + interval '1 minute'
  ),
  (
    'ffffffff-ffff-ffff-ffff-ffffffffff02',
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee1',
    'assistant',
    'Acme offers Starter (up to 5 seats), Pro (up to 50), and Enterprise (custom). I can summarize pricing if you tell me your team size.',
    'openai',
    'gpt-4o',
    42,
    890,
    now() - interval '3 days' + interval '1 minute' + interval '2 seconds'
  ),
  (
    'ffffffff-ffff-ffff-ffff-ffffffffff03',
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee1',
    'user',
    'We are 12 people.',
    'openai',
    'gpt-4o',
    8,
    NULL,
    now() - interval '3 days' + interval '5 minutes'
  ),
  (
    'ffffffff-ffff-ffff-ffff-ffffffffff04',
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee1',
    'assistant',
    'For 12 people, **Pro** is usually the best fit. Want a link to the pricing page?',
    'openai',
    'gpt-4o',
    35,
    720,
    now() - interval '3 days' + interval '5 minutes' + interval '2 seconds'
  ),
  (
    'ffffffff-ffff-ffff-ffff-ffffffffff05',
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee3',
    'user',
    'I was double-billed last month. Account email is user@example.com.',
    'anthropic',
    'claude-sonnet-4-20250514',
    22,
    NULL,
    now() - interval '6 hours'
  ),
  (
    'ffffffff-ffff-ffff-ffff-ffffffffff06',
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee3',
    'assistant',
    'Sorry that happened. I cannot access billing systems. I will flag this for our billing team — please expect an email within one business day.',
    'anthropic',
    'claude-sonnet-4-20250514',
    55,
    1100,
    now() - interval '6 hours' + interval '3 seconds'
  ),
  (
    'ffffffff-ffff-ffff-ffff-ffffffffff07',
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee4',
    'user',
    'How do I export my data?',
    'groq',
    'llama-3.3-70b-versatile',
    12,
    NULL,
    now() - interval '30 minutes'
  ),
  (
    'ffffffff-ffff-ffff-ffff-ffffffffff08',
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee4',
    'assistant',
    'Go to **Settings → Data → Export**. You will receive a ZIP with CSV and JSON within a few minutes.',
    'groq',
    'llama-3.3-70b-versatile',
    48,
    410,
    now() - interval '28 minutes'
  );

-- Align message_count on sessions with actual rows (schema default is 0)
UPDATE chat_sessions SET message_count = 4 WHERE id = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee1';
UPDATE chat_sessions SET message_count = 2 WHERE id = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee3';
UPDATE chat_sessions SET message_count = 2 WHERE id = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee4';

-- ---------------------------------------------------------------------------
-- Usage events (billing / analytics)
-- ---------------------------------------------------------------------------
INSERT INTO usage_events (
  id,
  client_id,
  session_id,
  event_type,
  api_provider,
  model_used,
  tokens_input,
  tokens_output,
  cost_usd,
  created_at
)
VALUES
  (
    '99999999-9999-9999-9999-999999990001',
    'cccccccc-cccc-cccc-cccc-ccccccccccc1',
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee1',
    'chat.completion',
    'openai',
    'gpt-4o',
    18,
    42,
    0.001234,
    now() - interval '3 days' + interval '1 minute'
  ),
  (
    '99999999-9999-9999-9999-999999990002',
    'cccccccc-cccc-cccc-cccc-ccccccccccc1',
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee1',
    'chat.completion',
    'openai',
    'gpt-4o',
    8,
    35,
    0.000987,
    now() - interval '3 days' + interval '5 minutes'
  ),
  (
    '99999999-9999-9999-9999-999999990003',
    'cccccccc-cccc-cccc-cccc-ccccccccccc2',
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee3',
    'chat.completion',
    'anthropic',
    'claude-sonnet-4-20250514',
    22,
    55,
    0.002100,
    now() - interval '6 hours'
  ),
  (
    '99999999-9999-9999-9999-999999990004',
    'cccccccc-cccc-cccc-cccc-ccccccccccc3',
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee4',
    'chat.completion',
    'groq',
    'llama-3.3-70b-versatile',
    12,
    48,
    0.000045,
    now() - interval '28 minutes'
  ),
  (
    '99999999-9999-9999-9999-999999990005',
    'cccccccc-cccc-cccc-cccc-ccccccccccc3',
    NULL,
    'chat.completion',
    'groq',
    'llama-3.3-70b-versatile',
    5,
    12,
    0.000010,
    now() - interval '1 day'
  );
