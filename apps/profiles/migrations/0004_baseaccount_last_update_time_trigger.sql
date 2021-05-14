CREATE OR REPLACE FUNCTION update_last_update_time_4_base_accounts()
RETURNS TRIGGER AS
$func$
BEGIN
    NEW."last_update_time" := now();
    RETURN NEW;
END
$func$ LANGUAGE plpgsql;


CREATE TRIGGER update_last_update_time_4_base_accounts_trigger
    BEFORE INSERT OR UPDATE
    ON base_accounts
    FOR EACH ROW
    EXECUTE PROCEDURE update_last_update_time_4_base_accounts();
