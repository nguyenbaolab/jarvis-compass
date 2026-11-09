-- Ngày, ưu tiên, sức, và lịch sử dời việc. CLI bọc cả file trong một transaction.

alter table public.plans
    add column priority text;

alter table public.plans
    add constraint plans_priority_known
    check (priority is null or priority in ('high', 'medium', 'low'));

alter table public.subtasks
    add column scheduled_on date,
    add column effort text;

alter table public.subtasks
    add constraint subtasks_effort_known
    check (effort is null or effort in ('S', 'M', 'L'));

create table public.subtask_date_moves (
    id uuid primary key default gen_random_uuid(),
    plan_id uuid not null,
    subtask_id uuid not null,
    from_date date not null,
    to_date date not null,
    reason text,
    moved_at timestamptz not null,
    constraint subtask_date_moves_dates_differ check (to_date <> from_date)
);

alter table public.subtask_date_moves enable row level security;

grant select, insert, update, delete on public.subtask_date_moves to service_role;

create function public.subtask_date_moves_block_change()
returns trigger
language plpgsql
set search_path = public
as $$
begin
    raise exception 'subtask_date_moves_append_only';
end;
$$;

create trigger subtask_date_moves_no_change
before update or delete on public.subtask_date_moves
for each row
execute function public.subtask_date_moves_block_change();

drop function public.add_plan(text, jsonb);

create function public.add_plan(goal text, subtasks jsonb, priority text default null)
returns jsonb
language plpgsql
set search_path = public
as $$
declare
    new_id uuid;
    elem record;
    new_date date;
    new_effort text;
begin
    insert into public.plans (goal, priority)
    values (add_plan.goal, add_plan.priority)
    returning id into new_id;

    for elem in
        select value, ordinality
        from jsonb_array_elements(subtasks) with ordinality
    loop
        if not (elem.value ? 'scheduled_on') or jsonb_typeof(elem.value->'scheduled_on') = 'null' then
            new_date := null;
        else
            new_date := (elem.value->>'scheduled_on')::date;
        end if;
        if not (elem.value ? 'effort') or jsonb_typeof(elem.value->'effort') = 'null' then
            new_effort := null;
        else
            new_effort := elem.value->>'effort';
        end if;
        insert into public.subtasks (
            id, plan_id, title, status, note, position, scheduled_on, effort
        )
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
            (elem.ordinality - 1)::integer,
            new_date,
            new_effort
        );
    end loop;

    return (
        select jsonb_build_object(
            'id', p.id,
            'goal', p.goal,
            'created_order', p.created_order,
            'version', p.version,
            'priority', p.priority,
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
                            'status_changed_at', s.status_changed_at,
                            'scheduled_on', s.scheduled_on,
                            'effort', s.effort
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

revoke all on function public.add_plan(text, jsonb, text) from public, anon, authenticated;
grant execute on function public.add_plan(text, jsonb, text) to service_role;

drop function public.replace_plan(uuid, text, jsonb, integer);

create function public.replace_plan(
    plan_id uuid,
    goal text,
    subtasks jsonb,
    expected_version integer,
    plan_fields jsonb default null,
    move_reason text default null,
    moved_at timestamptz default null
)
returns boolean
language plpgsql
set search_path = public
as $$
declare
    elem record;
    updated_id uuid;
    sub_id uuid;
    old_on date;
    old_effort text;
    new_on date;
    new_effort text;
    found_row boolean;
begin
    update public.plans
    set
        goal = replace_plan.goal,
        version = public.plans.version + 1,
        priority = case
            when plan_fields is null or not (plan_fields ? 'priority') then public.plans.priority
            when jsonb_typeof(plan_fields->'priority') = 'null' then null
            else plan_fields->>'priority'
        end
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
        sub_id := (elem.value->>'id')::uuid;
        old_on := null;
        old_effort := null;
        select s.scheduled_on, s.effort
        into old_on, old_effort
        from public.subtasks s
        where s.plan_id = replace_plan.plan_id
          and s.id = sub_id;
        found_row := found;

        if not found_row then
            if not (elem.value ? 'scheduled_on')
               or jsonb_typeof(elem.value->'scheduled_on') = 'null' then
                new_on := null;
            else
                new_on := (elem.value->>'scheduled_on')::date;
            end if;
        elsif not (elem.value ? 'scheduled_on') then
            new_on := old_on;
        elsif jsonb_typeof(elem.value->'scheduled_on') = 'null' then
            new_on := null;
        else
            new_on := (elem.value->>'scheduled_on')::date;
        end if;

        if not found_row then
            if not (elem.value ? 'effort')
               or jsonb_typeof(elem.value->'effort') = 'null' then
                new_effort := null;
            else
                new_effort := elem.value->>'effort';
            end if;
        elsif not (elem.value ? 'effort') then
            new_effort := old_effort;
        elsif jsonb_typeof(elem.value->'effort') = 'null' then
            new_effort := null;
        else
            new_effort := elem.value->>'effort';
        end if;

        if found_row
           and old_on is not null
           and new_on is not null
           and old_on <> new_on then
            if moved_at is null then
                raise exception 'moved_at_required' using errcode = 'P0001';
            end if;
            insert into public.subtask_date_moves (
                plan_id, subtask_id, from_date, to_date, reason, moved_at
            )
            values (
                replace_plan.plan_id,
                sub_id,
                old_on,
                new_on,
                move_reason,
                moved_at
            );
        end if;

        update public.subtasks
        set
            title = elem.value->>'title',
            status = elem.value->>'status',
            note = case
                when jsonb_typeof(elem.value->'note') = 'null' then null
                when not (elem.value ? 'note') then null
                else elem.value->>'note'
            end,
            position = (elem.ordinality - 1)::integer,
            scheduled_on = new_on,
            effort = new_effort
        where public.subtasks.plan_id = replace_plan.plan_id
          and public.subtasks.id = sub_id;

        if not found then
            insert into public.subtasks (
                id, plan_id, title, status, note, position, scheduled_on, effort
            )
            values (
                sub_id,
                replace_plan.plan_id,
                elem.value->>'title',
                elem.value->>'status',
                case
                    when jsonb_typeof(elem.value->'note') = 'null' then null
                    when not (elem.value ? 'note') then null
                    else elem.value->>'note'
                end,
                (elem.ordinality - 1)::integer,
                new_on,
                new_effort
            );
        end if;
    end loop;
    return true;
end;
$$;

revoke all on function public.replace_plan(uuid, text, jsonb, integer, jsonb, text, timestamptz)
    from public, anon, authenticated;
grant execute on function public.replace_plan(uuid, text, jsonb, integer, jsonb, text, timestamptz)
    to service_role;
