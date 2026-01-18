create extension if not exists pgcrypto;

alter table user_profiles
    add column if not exists id uuid;

update user_profiles
   set id = gen_random_uuid()
 where id is null;

alter table user_profiles
    alter column id set default gen_random_uuid(),
    alter column id set not null;

alter table threads
    drop constraint if exists threads_user_profile_id_fkey;

alter table user_profiles
    drop constraint if exists user_profiles_pkey;

alter table user_profiles
    add constraint user_profiles_pkey primary key (id);

alter table user_profiles
    add column if not exists stack_user_id uuid;

alter table user_profiles
    alter column customer_profile drop not null;

create unique index if not exists user_profiles_stack_user_id_key on user_profiles (stack_user_id);
create unique index if not exists user_profiles_customer_profile_key on user_profiles (customer_profile);

alter table threads
    add column if not exists user_id uuid;

update threads t
   set user_id = up.id
  from user_profiles up
 where t.customer_profile = up.customer_profile
   and t.user_id is null;

alter table threads
    add constraint threads_user_profiles_id_fkey
        foreign key (user_id) references user_profiles(id) on delete set null;

alter table threads
    drop column if exists customer_profile;
