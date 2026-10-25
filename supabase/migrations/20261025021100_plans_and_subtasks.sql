-- plans, subtasks, trigger mốc thời gian, và hai RPC ghi.

create schema if not exists internal;

revoke all on schema internal from public;
revoke all on schema internal from anon, authenticated;
grant usage on schema internal to service_role;

create table public.plans (
    id uuid primary key default gen_random_uuid(),
    goal text not null,
    created_order bigint generated always as identity unique
);

create table public.subtasks (
    id uuid primary key,
    plan_id uuid not null references public.plans (id) on delete cascade,
    title text not null,
    status text not null,
    note text,
    position integer not null,
    created_at timestamptz not null default now(),
    status_changed_at timestamptz not null default now(),
    constraint subtasks_status_known check (status in ('pending', 'done', 'skipped')),
    constraint subtasks_note_empty check (note is null or note <> ''),
    constraint subtasks_position_unique unique (plan_id, position) deferrable initially deferred
);

alter table public.plans enable row level security;
alter table public.subtasks enable row level security;

create function internal.subtasks_keep_clocks()
returns trigger
language plpgsql
set search_path = public
as $$
begin
    new.created_at := old.created_at;
    if new.status is distinct from old.status then
        new.status_changed_at := now();
    else
        new.status_changed_at := old.status_changed_at;
    end if;
    return new;
end;
$$;

create trigger subtasks_keep_clocks
before update on public.subtasks
for each row
execute function internal.subtasks_keep_clocks();

create function public.add_plan(goal text, subtasks jsonb)
returns jsonb
language plpgsql
set search_path = public
as $$
declare
    new_id uuid;
    elem record;
begin
    insert into public.plans (goal)
    values (add_plan.goal)
    returning id into new_id;

    for elem in
        select value, ordinality
        from jsonb_array_elements(subtasks) with ordinality
    loop
        insert into public.subtasks (id, plan_id, title, status, note, position)
        values (
            (elem.value->>'id')::uuid,
            new_id,
            elem.value->>'title',
            elem.value->>'status',
            case
                when jsonb_typeof(elem.value->'note') = 'null' then null
                when not (elem.value ? 'note') then null
                else elem.value->>'note'
            end,
            (elem.ordinality - 1)::integer
        );
    end loop;

    return (
        select jsonb_build_object(
            'id', p.id,
            'goal', p.goal,
            'created_order', p.created_order,
            'subtasks', coalesce(
                (
                    select jsonb_agg(
                        jsonb_build_object(
                            'id', s.id,
                            'title', s.title,
                            'status', s.status,
                            'note', s.note,
                            'position', s.position,
                            'created_at', s.created_at,
                            'status_changed_at', s.status_changed_at
                        )
                        order by s.position
                    )
                    from public.subtasks s
                    where s.plan_id = p.id
                ),
                '[]'::jsonb
            )
        )
        from public.plans p
        where p.id = new_id
    );
end;
$$;

create function public.replace_plan(plan_id uuid, goal text, subtasks jsonb)
returns void
language plpgsql
set search_path = public
as $$
declare
    elem record;
begin
    if not exists (select 1 from public.plans p where p.id = replace_plan.plan_id) then
        raise exception 'plan_missing' using errcode = 'P0001';
    end if;

    update public.plans
    set goal = replace_plan.goal
    where id = replace_plan.plan_id;

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
end;
$$;

revoke all on table public.plans from public, anon, authenticated;
revoke all on table public.subtasks from public, anon, authenticated;
revoke all on function public.add_plan(text, jsonb) from public, anon, authenticated;
revoke all on function public.replace_plan(uuid, text, jsonb) from public, anon, authenticated;
revoke all on function internal.subtasks_keep_clocks() from public, anon, authenticated;
revoke all on sequence public.plans_created_order_seq from public, anon, authenticated;

grant select, insert, update, delete on table public.plans to service_role;
grant select, insert, update, delete on table public.subtasks to service_role;
grant usage, select on sequence public.plans_created_order_seq to service_role;
grant execute on function public.add_plan(text, jsonb) to service_role;
grant execute on function public.replace_plan(uuid, text, jsonb) to service_role;
