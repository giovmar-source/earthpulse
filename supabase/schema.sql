-- Tabelle di EarthPulse su Supabase (Postgres). Da eseguire una volta nell'editor SQL
-- del progetto Supabase (regione UE, es. Frankfurt eu-central-1).
-- Sicurezza: Row Level Security attiva ovunque. Il sito (chiave pubblicabile) vede solo
-- le righe del proprio utente; piani e contatori li scrive solo il server.

-- Piano di ogni utente: lo scrive solo il webhook dei pagamenti (server)
create table if not exists public.subscriptions (
  user_id uuid primary key references auth.users(id) on delete cascade,
  plan text not null default 'free' check (plan in ('free', 'pro', 'institutional')),
  status text not null default 'active',
  current_period_end timestamptz,
  paddle_subscription_id text,
  last_event_id text,
  last_event_at timestamptz,
  updated_at timestamptz not null default now()
);
alter table public.subscriptions enable row level security;
create policy "leggo il mio piano" on public.subscriptions for select to authenticated
  using ((select auth.uid()) = user_id);

-- Uso giornaliero (luoghi analizzati, esportazioni): solo il server
create table if not exists public.usage_events (
  user_id uuid not null references auth.users(id) on delete cascade,
  day date not null default current_date,
  kind text not null,
  item text not null,
  created_at timestamptz not null default now(),
  primary key (user_id, day, kind, item)
);
alter table public.usage_events enable row level security;   -- nessuna policy: solo il server

-- Luoghi salvati: li gestisce il sito direttamente, ognuno solo i propri
create table if not exists public.saved_places (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  name text not null,
  lat double precision not null check (lat between -90 and 90),
  lon double precision not null check (lon between -180 and 180),
  note text,
  created_at timestamptz not null default now()
);
alter table public.saved_places enable row level security;
create policy "i miei luoghi" on public.saved_places for all to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

-- Avvisi automatici su un luogo salvato
create table if not exists public.alerts (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  place_id bigint not null references public.saved_places(id) on delete cascade,
  kind text not null check (kind in ('fires', 'new_water')),
  radius_km integer not null default 25 check (radius_km between 5 and 100),
  threshold double precision,
  active boolean not null default true,
  created_at timestamptz not null default now()
);
alter table public.alerts enable row level security;
create policy "i miei avvisi" on public.alerts for all to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

-- Avvisi già inviati (per non mandare due volte lo stesso): solo il server
create table if not exists public.alert_events (
  alert_id bigint not null references public.alerts(id) on delete cascade,
  fingerprint text not null,
  sent_at timestamptz not null default now(),
  primary key (alert_id, fingerprint)
);
alter table public.alert_events enable row level security;

revoke all on public.saved_places, public.alerts from anon;

-- Limiti dei piani su luoghi salvati e avvisi, controllati dal database.
-- Tenere allineati con src/plans.py (saved_places, alerts).
create or replace function public.plan_limit(kind text) returns integer
language sql stable security definer set search_path = public as $$
  select case coalesce((select plan from public.subscriptions s
                        where s.user_id = auth.uid() and s.status in ('active', 'trialing')
                          and (s.current_period_end is null or s.current_period_end > now())), 'free')
    when 'pro' then case kind when 'saved_places' then 100 else 25 end
    when 'institutional' then case kind when 'saved_places' then 2000 else 300 end
    else case kind when 'saved_places' then 3 else 0 end
  end;
$$;

create or replace function public.check_saved_places_limit() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if (select count(*) from public.saved_places where user_id = new.user_id) >= public.plan_limit('saved_places') then
    raise exception 'Hai raggiunto il numero di luoghi salvabili con il tuo piano';
  end if;
  return new;
end $$;
drop trigger if exists saved_places_limit on public.saved_places;
create trigger saved_places_limit before insert on public.saved_places
  for each row execute function public.check_saved_places_limit();

create or replace function public.check_alerts_limit() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if (select count(*) from public.alerts where user_id = new.user_id) >= public.plan_limit('alerts') then
    raise exception 'Gli avvisi automatici sono inclusi nei piani Pro e Istituzionale';
  end if;
  return new;
end $$;
drop trigger if exists alerts_limit on public.alerts;
create trigger alerts_limit before insert on public.alerts
  for each row execute function public.check_alerts_limit();
