-- Access grants compiled from governance/access_policy.yaml and users.yaml.
-- PostgreSQL-compatible syntax. Regenerate with `govkit docs`; never edit by hand.

CREATE ROLE gov_customer_data_consumer NOLOGIN;
CREATE ROLE gov_customer_data_owner NOLOGIN;
CREATE ROLE gov_customer_data_steward NOLOGIN;
CREATE ROLE gov_data_custodian NOLOGIN;
CREATE ROLE gov_data_sponsor NOLOGIN;
CREATE ROLE gov_governance_council NOLOGIN;
CREATE ROLE gov_operations_data_consumer NOLOGIN;
CREATE ROLE gov_operations_data_owner NOLOGIN;
CREATE ROLE gov_operations_data_steward NOLOGIN;
CREATE ROLE gov_supply_chain_data_consumer NOLOGIN;
CREATE ROLE gov_supply_chain_data_owner NOLOGIN;
CREATE ROLE gov_supply_chain_data_steward NOLOGIN;

GRANT gov_customer_data_consumer TO "robin.notreal@example.org";
GRANT gov_customer_data_owner TO "taylor.dummond@example.org";
GRANT gov_customer_data_steward TO "alex.exampleton@example.org";
GRANT gov_data_custodian TO "drew.stubbs@example.org";
GRANT gov_data_sponsor TO "morgan.fictive@example.org";
GRANT gov_governance_council TO "quinn.synthia@example.org";
GRANT gov_operations_data_consumer TO "jamie.fakeley@example.org";
GRANT gov_operations_data_owner TO "riley.placeholder@example.org";
GRANT gov_operations_data_steward TO "sam.samplewood@example.org";
GRANT gov_supply_chain_data_consumer TO "jamie.fakeley@example.org";
GRANT gov_supply_chain_data_owner TO "jordan.mockwell@example.org";
GRANT gov_supply_chain_data_steward TO "casey.testa@example.org";

GRANT SELECT ON bronze.assets TO gov_data_custodian;
GRANT SELECT ON bronze.assets TO gov_operations_data_steward;
GRANT SELECT ON bronze.customers TO gov_customer_data_steward;
GRANT SELECT ON bronze.customers TO gov_data_custodian;  -- personal data masked
GRANT SELECT ON bronze.labor_entries TO gov_data_custodian;
GRANT SELECT ON bronze.labor_entries TO gov_operations_data_steward;
GRANT SELECT ON bronze.material_issues TO gov_data_custodian;
GRANT SELECT ON bronze.material_issues TO gov_supply_chain_data_steward;
GRANT SELECT ON bronze.materials TO gov_data_custodian;
GRANT SELECT ON bronze.materials TO gov_supply_chain_data_steward;
GRANT SELECT ON bronze.service_orders TO gov_data_custodian;
GRANT SELECT ON bronze.service_orders TO gov_operations_data_steward;
GRANT SELECT ON bronze.technicians TO gov_operations_data_steward;
