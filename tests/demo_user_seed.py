import subprocess


DEMO_PASSWORD_HASH = "$2b$10$CwTycUXWue0Thq9StjUM0uJ8TGTSt1n1.Ki/hxL7s.1UTMwuY5M2G"


def seed_demo_inspectors(plan, compose_file: str, project_name: str) -> None:
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            compose_file,
            "-p",
            project_name,
            "exec",
            "-T",
            "postgres",
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "postgres",
            "-d",
            "user_service",
        ],
        input=render_demo_inspector_sql(plan),
        text=True,
        check=True,
    )


def render_demo_inspector_sql(plan) -> str:
    inspector_ids = tuple(inspector_id for brigade in plan.brigades for inspector_id in brigade.inspector_ids)
    user_ids = ", ".join(str(inspector_id) for inspector_id in inspector_ids)
    users = ",\n".join(
        "("
        f"{inspector_id}, 1, 'Инспектор', 'Демо', 'Тестовый', "
        f"'+7910{inspector_id:07d}', 'demo.inspector.{inspector_id}@energo.local', "
        f"'{DEMO_PASSWORD_HASH}', now(), now()"
        ")"
        for inspector_id in inspector_ids
    )
    return f"""
create table if not exists users (
    id serial primary key,
    role_id integer not null,
    surname text not null,
    name text not null,
    patronymic text,
    phone_number text not null unique,
    email text not null unique,
    password_hash text not null,
    refresh_token text,
    refresh_token_expired_after timestamp with time zone,
    created_at timestamp with time zone default now() not null,
    updated_at timestamp with time zone default now() not null,
    constraint phone_number_format check (phone_number ~ '^(\\+7|8)\\d{{10}}$'),
    constraint email_format check (email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{{2,}}$')
);
delete from users where id in ({user_ids});
insert into users (id, role_id, surname, name, patronymic, phone_number, email, password_hash, created_at, updated_at) overriding system value values
{users};
"""
