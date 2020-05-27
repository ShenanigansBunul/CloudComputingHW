create table if not exists users
(
    id              serial primary key,
    discord_id      bigint    not null unique,
    last_known_name text      not null,
    first_seen      timestamp not null,
    money           integer   not null default 0
);

create table if not exists packs
(
    id         serial primary key,
    name       text      not null,
    photo      bytea,
    created    timestamp not null,
    created_by integer   not null references users (id),
    guild_id   bigint    not null,
    price      integer   not null,
    unique (name, guild_id)
);

create table if not exists collectibles
(
    id                serial primary key,
    name              text      not null,
    description       text      not null,
    rarity            text      not null,
    photo             bytea,
    created           timestamp not null,
    created_by        integer   not null references users (id),
    created_on_server bigint    not null
);

create table if not exists pack_collectibles
(
    pack_id        integer not null references packs (id),
    collectible_id integer not null references collectibles (id)
);

create table if not exists user_collectibles
(
    user_id        integer not null references users (id),
    collectible_id integer not null references collectibles (id)
);