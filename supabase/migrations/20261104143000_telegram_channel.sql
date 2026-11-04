-- telegram_updates, telegram_context_messages, và năm RPC của kênh.

create table public.telegram_updates (
    update_id bigint primary key,
    started_at timestamptz not null,
    reply text,
    sent_at timestamptz
);

create table public.telegram_context_messages (
    update_id bigint not null references public.telegram_updates (update_id),
    role text not null,
    chat_id bigint not null,
    body text not null,
    saved_at timestamptz not null,
    primary key (update_id, role),
    constraint telegram_context_messages_role_known check (role in ('user', 'assistant'))
);

alter table public.telegram_updates enable row level security;
alter table public.telegram_context_messages enable row level security;

create function public.claim_telegram_update(p_update_id bigint, p_started_at timestamptz)
returns jsonb
language plpgsql
set search_path = public
as $$
declare
    inserted_count integer;
    found_row public.telegram_updates;
begin
    insert into public.telegram_updates (update_id, started_at)
    values (p_update_id, p_started_at)
    on conflict (update_id) do nothing;

    get diagnostics inserted_count = row_count;

    select *
    into found_row
    from public.telegram_updates
    where update_id = p_update_id;

    return jsonb_build_object(
        'update_id', found_row.update_id,
        'started_at', found_row.started_at,
        'reply', found_row.reply,
        'sent_at', found_row.sent_at,
        'inserted', inserted_count = 1
    );
end;
$$;

create function public.save_telegram_reply(p_update_id bigint, p_reply text)
returns boolean
language plpgsql
set search_path = public
as $$
declare
    changed integer;
begin
    update public.telegram_updates
    set reply = p_reply
    where update_id = p_update_id
      and reply is null;

    get diagnostics changed = row_count;
    return changed = 1;
end;
$$;

create function public.mark_telegram_sent(p_update_id bigint, p_sent_at timestamptz)
returns void
language plpgsql
set search_path = public
as $$
begin
    update public.telegram_updates
    set sent_at = p_sent_at
    where update_id = p_update_id
      and reply is not null
      and sent_at is null;
end;
$$;

create function public.append_telegram_context(
    p_update_id bigint,
    p_role text,
    p_chat_id bigint,
    p_body text,
    p_saved_at timestamptz
)
returns void
language plpgsql
set search_path = public
as $$
begin
    insert into public.telegram_context_messages (update_id, role, chat_id, body, saved_at)
    values (p_update_id, p_role, p_chat_id, p_body, p_saved_at)
    on conflict (update_id, role) do nothing;
end;
$$;

create function public.list_telegram_context(
    p_chat_id bigint,
    p_saved_at_gte timestamptz,
    p_limit integer
)
returns jsonb
language plpgsql
set search_path = public
as $$
begin
    return (
        select coalesce(
            jsonb_agg(
                jsonb_build_object(
                    'update_id', picked.update_id,
                    'role', picked.role,
                    'chat_id', picked.chat_id,
                    'body', picked.body,
                    'saved_at', picked.saved_at
                )
                order by picked.saved_at desc, picked.role desc
            ),
            '[]'::jsonb
        )
        from (
            select update_id, role, chat_id, body, saved_at
            from public.telegram_context_messages
            where chat_id = p_chat_id
              and saved_at >= p_saved_at_gte
            order by saved_at desc, role desc
            limit p_limit
        ) picked
    );
end;
$$;

revoke all on table public.telegram_updates from public, anon, authenticated;
revoke all on table public.telegram_context_messages from public, anon, authenticated;
revoke all on function public.claim_telegram_update(bigint, timestamptz) from public, anon, authenticated;
revoke all on function public.save_telegram_reply(bigint, text) from public, anon, authenticated;
revoke all on function public.mark_telegram_sent(bigint, timestamptz) from public, anon, authenticated;
revoke all on function public.append_telegram_context(bigint, text, bigint, text, timestamptz) from public, anon, authenticated;
revoke all on function public.list_telegram_context(bigint, timestamptz, integer) from public, anon, authenticated;

grant select, insert, update, delete on table public.telegram_updates to service_role;
grant select, insert, update, delete on table public.telegram_context_messages to service_role;
grant execute on function public.claim_telegram_update(bigint, timestamptz) to service_role;
grant execute on function public.save_telegram_reply(bigint, text) to service_role;
grant execute on function public.mark_telegram_sent(bigint, timestamptz) to service_role;
grant execute on function public.append_telegram_context(bigint, text, bigint, text, timestamptz) to service_role;
grant execute on function public.list_telegram_context(bigint, timestamptz, integer) to service_role;
