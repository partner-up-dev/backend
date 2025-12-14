-- create roles and grant privileges
CREATE ROLE anonymous NOLOGIN;
GRANT USAGE ON SCHEMA public TO anonymous;
GRANT SELECT, INSERT, UPDATE ON public.location TO anonymous;