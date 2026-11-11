-- Access grants compiled from governance/access_policy.yaml and users.yaml.
-- PostgreSQL-compatible syntax. Regenerate with `govkit docs`; never edit by hand.

CREATE ROLE gov_auditor NOLOGIN;
CREATE ROLE gov_customer_data_consumer NOLOGIN;
CREATE ROLE gov_customer_data_owner NOLOGIN;
CREATE ROLE gov_customer_data_steward NOLOGIN;
CREATE ROLE gov_customer_field_technician NOLOGIN;
CREATE ROLE gov_data_custodian NOLOGIN;
CREATE ROLE gov_data_sponsor NOLOGIN;
CREATE ROLE gov_governance_council NOLOGIN;
CREATE ROLE gov_operations_data_consumer NOLOGIN;
CREATE ROLE gov_operations_data_owner NOLOGIN;
CREATE ROLE gov_operations_data_steward NOLOGIN;
CREATE ROLE gov_operations_field_technician NOLOGIN;
CREATE ROLE gov_supply_chain_data_consumer NOLOGIN;
CREATE ROLE gov_supply_chain_data_owner NOLOGIN;
CREATE ROLE gov_supply_chain_data_steward NOLOGIN;
CREATE ROLE gov_supply_chain_field_technician NOLOGIN;

GRANT gov_auditor TO "ellis.checkwell@example.org";
GRANT gov_customer_data_consumer TO "robin.notreal@example.org";
GRANT gov_customer_data_owner TO "taylor.dummond@example.org";
GRANT gov_customer_data_steward TO "alex.exampleton@example.org";
GRANT gov_data_custodian TO "drew.stubbs@example.org";
GRANT gov_data_sponsor TO "morgan.fictive@example.org";
GRANT gov_governance_council TO "quinn.synthia@example.org";
GRANT gov_operations_data_consumer TO "jamie.fakeley@example.org";
GRANT gov_operations_data_owner TO "riley.placeholder@example.org";
GRANT gov_operations_data_steward TO "sam.samplewood@example.org";
GRANT gov_operations_field_technician TO "rowan.pretendez@example.org";
GRANT gov_supply_chain_data_consumer TO "jamie.fakeley@example.org";
GRANT gov_supply_chain_data_owner TO "jordan.mockwell@example.org";
GRANT gov_supply_chain_data_steward TO "casey.testa@example.org";

GRANT SELECT ON bronze.assets TO gov_auditor;
GRANT SELECT ON bronze.assets TO gov_data_custodian;
GRANT SELECT ON bronze.assets TO gov_operations_data_steward;
GRANT SELECT ON bronze.customers TO gov_auditor;  -- personal data masked
GRANT SELECT ON bronze.customers TO gov_customer_data_steward;
GRANT SELECT ON bronze.customers TO gov_data_custodian;  -- personal data masked
GRANT SELECT ON bronze.labor_entries TO gov_auditor;
GRANT SELECT ON bronze.labor_entries TO gov_data_custodian;
GRANT SELECT ON bronze.labor_entries TO gov_operations_data_steward;
GRANT SELECT ON bronze.material_issues TO gov_auditor;
GRANT SELECT ON bronze.material_issues TO gov_data_custodian;
GRANT SELECT ON bronze.material_issues TO gov_supply_chain_data_steward;
GRANT SELECT ON bronze.materials TO gov_auditor;
GRANT SELECT ON bronze.materials TO gov_data_custodian;
GRANT SELECT ON bronze.materials TO gov_supply_chain_data_steward;
GRANT SELECT ON bronze.service_orders TO gov_auditor;
GRANT SELECT ON bronze.service_orders TO gov_data_custodian;
GRANT SELECT ON bronze.service_orders TO gov_operations_data_steward;
GRANT SELECT ON bronze.technicians TO gov_auditor;  -- personal data masked
GRANT SELECT ON bronze.technicians TO gov_operations_data_steward;
GRANT SELECT ON gold.customer_value TO gov_auditor;  -- personal data masked
GRANT SELECT ON gold.customer_value TO gov_customer_data_owner;
GRANT SELECT ON gold.customer_value TO gov_customer_data_steward;
GRANT SELECT ON gold.customer_value TO gov_data_custodian;  -- personal data masked
GRANT SELECT ON gold.customer_value TO gov_governance_council;  -- personal data masked
GRANT SELECT ON gold.inventory_position TO gov_auditor;
GRANT SELECT ON gold.inventory_position TO gov_data_custodian;
GRANT SELECT ON gold.inventory_position TO gov_data_sponsor;
GRANT SELECT ON gold.inventory_position TO gov_governance_council;
GRANT SELECT ON gold.inventory_position TO gov_supply_chain_data_consumer;
GRANT SELECT ON gold.inventory_position TO gov_supply_chain_data_owner;
GRANT SELECT ON gold.inventory_position TO gov_supply_chain_data_steward;
GRANT SELECT ON gold.inventory_position TO gov_supply_chain_field_technician;
GRANT SELECT ON gold.service_order_economics TO gov_auditor;
GRANT SELECT ON gold.service_order_economics TO gov_data_custodian;
GRANT SELECT ON gold.service_order_economics TO gov_governance_council;
GRANT SELECT ON gold.service_order_economics TO gov_operations_data_owner;
GRANT SELECT ON gold.service_order_economics TO gov_operations_data_steward;
GRANT SELECT ON gold.service_order_economics TO "jamie.fakeley@example.org";  -- AR-0001, expires 2026-12-30
GRANT SELECT ON gold.site_monthly_kpis TO gov_auditor;
GRANT SELECT ON gold.site_monthly_kpis TO gov_data_custodian;
GRANT SELECT ON gold.site_monthly_kpis TO gov_governance_council;
GRANT SELECT ON gold.site_monthly_kpis TO gov_operations_data_owner;
GRANT SELECT ON gold.site_monthly_kpis TO gov_operations_data_steward;
GRANT SELECT ON gold.site_monthly_kpis TO "jamie.fakeley@example.org";  -- AR-0001, expires 2026-12-30
GRANT SELECT ON silver.assets TO gov_auditor;
GRANT SELECT ON silver.assets TO gov_data_custodian;
GRANT SELECT ON silver.assets TO gov_operations_data_owner;
GRANT SELECT ON silver.assets TO gov_operations_data_steward;
GRANT SELECT ON silver.assets TO gov_operations_field_technician;
GRANT SELECT ON silver.customers TO gov_auditor;  -- personal data masked
GRANT SELECT ON silver.customers TO gov_customer_data_owner;
GRANT SELECT ON silver.customers TO gov_customer_data_steward;
GRANT SELECT ON silver.customers TO gov_data_custodian;  -- personal data masked
GRANT SELECT ON silver.labor_entries TO gov_auditor;
GRANT SELECT ON silver.labor_entries TO gov_data_custodian;
GRANT SELECT ON silver.labor_entries TO gov_operations_data_owner;
GRANT SELECT ON silver.labor_entries TO gov_operations_data_steward;
GRANT SELECT ON silver.labor_entries TO gov_operations_field_technician;
GRANT SELECT ON silver.material_issues TO gov_auditor;
GRANT SELECT ON silver.material_issues TO gov_data_custodian;
GRANT SELECT ON silver.material_issues TO gov_supply_chain_data_owner;
GRANT SELECT ON silver.material_issues TO gov_supply_chain_data_steward;
GRANT SELECT ON silver.material_issues TO gov_supply_chain_field_technician;
GRANT SELECT ON silver.materials TO gov_auditor;
GRANT SELECT ON silver.materials TO gov_data_custodian;
GRANT SELECT ON silver.materials TO gov_supply_chain_data_owner;
GRANT SELECT ON silver.materials TO gov_supply_chain_data_steward;
GRANT SELECT ON silver.materials TO gov_supply_chain_field_technician;
GRANT SELECT ON silver.service_orders TO gov_auditor;
GRANT SELECT ON silver.service_orders TO gov_data_custodian;
GRANT SELECT ON silver.service_orders TO gov_operations_data_owner;
GRANT SELECT ON silver.service_orders TO gov_operations_data_steward;
GRANT SELECT (order_id, customer_id, asset_id, service_type, opened_on, closed_on, status, planned_hours) ON silver.service_orders TO gov_operations_field_technician;  -- without planned_labor_cost, planned_material_cost, price
GRANT SELECT ON silver.technicians TO gov_auditor;  -- personal data masked
GRANT SELECT ON silver.technicians TO gov_operations_data_owner;
GRANT SELECT ON silver.technicians TO gov_operations_data_steward;
