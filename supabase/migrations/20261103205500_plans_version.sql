-- version trên plans, add_plan trả version, replace_plan kiểm version atomic.

alter table public.plans
    add column version integer not null default 0;

create or replace function public.add_plan(goal text, subtasks jsonb)
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
            'version', p.version,
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

revoke all on function public.add_plan(text, jsonb) from public, anon, authenticated;
grant execute on function public.add_plan(text, jsonb) to service_role;

drop function public.replace_plan(uuid, text, jsonb);

create function public.replace_plan(
    plan_id uuid,
    goal text,
    subtasks jsonb,
    expected_version integer
)
returns void
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
end;
$$;

revoke all on function public.replace_plan(uuid, text, jsonb, integer) from public, anon, authenticated;
grant execute on function public.replace_plan(uuid, text, jsonb, integer) to service_role;
