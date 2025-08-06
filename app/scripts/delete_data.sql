BEGIN;

DO
$$
DECLARE
  t RECORD;
BEGIN
  FOR t IN
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_type = 'BASE TABLE'
  LOOP
    EXECUTE FORMAT(
      'TRUNCATE TABLE %I.%I RESTART IDENTITY CASCADE;',
      t.table_schema,
      t.table_name
    );
  END LOOP;
END
$$;

COMMIT;
