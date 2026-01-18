create table if not exists user_profiles (
    customer_profile int not null,
    name text,
    phone text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint user_profiles_pkey primary key (customer_profile)
);

create index if not exists user_profiles_customer_profile_idx on user_profiles (customer_profile);
create index if not exists user_profiles_phone_idx on user_profiles (phone);

alter table threads
    add column if not exists customer_profile int,
    add constraint threads_user_profile_id_fkey
        foreign key (customer_profile) references user_profiles(customer_profile) on delete set null;
