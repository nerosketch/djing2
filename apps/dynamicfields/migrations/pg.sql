-- Fill all user accounts with new dynamic field
CREATE OR REPLACE FUNCTION trigger_after_dynamic_field_insert () RETURNS trigger AS
$$
BEGIN
  INSERT INTO dynamic_field_content (customer_id, content, field_type_id)
  SELECT baseaccount_ptr_id, null, NEW.fieldmodel_id FROM customers WHERE group_id = NEW.group_id
--   ON CONFLICT (customer_id)
--   DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tfill_dfls
AFTER INSERT ON dynamic_fields_groups FOR EACH ROW
EXECUTE PROCEDURE trigger_after_dynamic_field_insert ();


-- Creates new empty dynamic field for new customers
-- Добавляем пустые записи динамических полей для созданного абонента
-- Добавляются только те поля, которые добавлены в ту же группу где создан абонент.
CREATE OR REPLACE FUNCTION trigger_after_customer_insert () RETURNS trigger AS
$$
BEGIN
  INSERT INTO dynamic_field_content (customer_id, content, field_type_id)
  SELECT NEW.baseaccount_ptr_id, null, fieldmodel_id FROM dynamic_fields_groups WHERE group_id = NEW.group_id;
--   ON CONFLICT (customer_id)
--   DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tfill_dfls_acc
AFTER INSERT ON customers FOR EACH ROW
EXECUTE PROCEDURE trigger_after_customer_insert ();
