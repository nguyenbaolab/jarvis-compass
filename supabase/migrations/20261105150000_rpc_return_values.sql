-- Ba RPC void thành boolean. PostgREST trả 204 không body cho hàm void và httpx trên Worker không đọc được (D-023).

drop function public.replace_plan(uuid, text, jsonb, integer);

create function public.replace_plan(
    plan_id uuid,
    goal text,
    subtasks jsonb,
    expected_version integer
)
returns boolean
language plpgsql
set search_path = public
as $$
declare
    elem record;
    updated_id uuid;
begin
    update public.plans
    set
        goal = replace_plan.goal,
        version = public.plans.version + 1
    where id = replace_plan.plan_id
      and version = expected_version
    returning id into updated_id;

    if updated_id is null then
        if not exists (select 1 from public.plans p where p.id = replace_plan.plan_id) then
            raise exception 'plan_missing' using errcode = 'P0001';
        end if;
        raise exception 'plan_version_conflict' using errcode = 'P0001';
    end if;

    delete from public.subtasks s
    where s.plan_id = replace_plan.plan_id
      and not exists (
          select 1
          from jsonb_array_elements(subtasks) as incoming(value)
          where (incoming.value->>'id')::uuid = s.id
      );

    for elem in
        select value, ordinality
        from jsonb_array_elements(subtasks) with ordinality
    loop
        update public.subtasks
        set
            title = elem.value->>'title',
            status = elem.value->>'status',
            note = case
                when jsonb_typeof(elem.value->'note') = 'null' then null
                when not (elem.value ? 'note') then null
                else elem.value->>'note'
            end,
            position = (elem.ordinality - 1)::integer
        where public.subtasks.plan_id = replace_plan.plan_id
          and public.subtasks.id = (elem.value->>'id')::uuid;

        if not found then
            insert into public.subtasks (id, plan_id, title, status, note, position)
            values (
                (elem.value->>'id')::uuid,
                replace_plan.plan_id,
                elem.value->>'title',
                elem.value->>'status',
                case
                    when jsonb_typeof(elem.value->'note') = 'null' then null
                    when not (elem.value ? 'note') then null
                    else elem.value->>'note'
                end,
                (elem.ordinality - 1)::integer
            );
        end if;
    end loop;
    return true;
end;
$$;

revoke all on function public.replace_plan(uuid, text, jsonb, integer) from public, anon, authenticated;
grant execute on function public.replace_plan(uuid, text, jsonb, integer) to service_role;

drop function public.mark_telegram_sent(bigint, timestamptz);

create function public.mark_telegram_sent(p_update_id bigint, p_sent_at timestamptz)
returns boolean
language plpgsql
set search_path = public
as $$
declare
    changed integer;
begin
    update public.telegram_updates
    set sent_at = p_sent_at
    where update_id = p_update_id
      and reply is not null
      and sent_at is null;
    get diagnostics changed = row_count;
    return changed = 1;
end;
$$;

revoke all on function public.mark_telegram_sent(bigint, timestamptz) from public, anon, authenticated;
grant execute on function public.mark_telegram_sent(bigint, timestamptz) to service_role;

drop function public.append_telegram_context(bigint, text, bigint, text, timestamptz);

create function public.append_telegram_context(
    p_update_id bigint,
    p_role text,
    p_chat_id bigint,
    p_body text,
    p_saved_at timestamptz
)
returns boolean
language plpgsql
set search_path = public
as $$
declare
    changed integer;
begin
    insert into public.telegram_context_messages (update_id, role, chat_id, body, saved_at)
    values (p_update_id, p_role, p_chat_id, p_body, p_saved_at)
    on conflict (update_id, role) do nothing;
    get diagnostics changed = row_count;
    return changed = 1;
end;
$$;

revoke all on function public.append_telegram_context(bigint, text, bigint, text, timestamptz) from public, anon, authenticated;
grant execute on function public.append_telegram_context(bigint, text, bigint, text, timestamptz) to service_role;
