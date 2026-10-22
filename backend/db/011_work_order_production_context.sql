-- 011_work_order_production_context.sql
-- Additive persistence for production ancestry context (site -> line -> station -> machine)
-- Normative source: private/wo-v2/AMENDMENT.md (ADR-002: production ancestry is not warehouse inventory)

CREATE TABLE IF NOT EXISTS pp.production_site (
    id TEXT PRIMARY KEY,
    company TEXT NOT NULL REFERENCES erp.company(name),
    name TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT uq_production_site_company_id UNIQUE (company, id)
);

CREATE TABLE IF NOT EXISTS pp.production_line (
    id TEXT PRIMARY KEY,
    company TEXT NOT NULL,
    site_id TEXT NOT NULL,
    name TEXT NOT NULL,
    production_scope TEXT NOT NULL CHECK (production_scope IN ('AC')),
    active BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT fk_production_line_site FOREIGN KEY (company, site_id) REFERENCES pp.production_site(company, id) ON DELETE RESTRICT,
    CONSTRAINT uq_production_line_company_id UNIQUE (company, id)
);

CREATE TABLE IF NOT EXISTS pp.production_station (
    id TEXT PRIMARY KEY,
    company TEXT NOT NULL,
    production_line_id TEXT NOT NULL,
    name TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT fk_production_station_line FOREIGN KEY (company, production_line_id) REFERENCES pp.production_line(company, id) ON DELETE RESTRICT,
    CONSTRAINT uq_production_station_company_id UNIQUE (company, id)
);

CREATE TABLE IF NOT EXISTS pp.machine_context (
    asset TEXT PRIMARY KEY REFERENCES erp.asset(name) ON DELETE RESTRICT,
    company TEXT NOT NULL REFERENCES erp.company(name) ON DELETE RESTRICT,
    station_id TEXT NOT NULL,
    CONSTRAINT fk_machine_context_station FOREIGN KEY (company, station_id) REFERENCES pp.production_station(company, id) ON DELETE RESTRICT
);

-- Indexes for reference reads
CREATE INDEX IF NOT EXISTS pp_production_site_company_idx ON pp.production_site (company, id);
CREATE INDEX IF NOT EXISTS pp_production_line_company_site_idx ON pp.production_line (company, site_id, id);
CREATE INDEX IF NOT EXISTS pp_production_station_company_line_idx ON pp.production_station (company, production_line_id, id);
CREATE INDEX IF NOT EXISTS pp_machine_context_company_station_asset_idx ON pp.machine_context (company, station_id, asset);

-- Constraint trigger to enforce asset.company = machine_context.company
CREATE OR REPLACE FUNCTION pp.check_machine_context_company_match()
RETURNS TRIGGER AS $$
DECLARE
    v_asset_company TEXT;
BEGIN
    SELECT company INTO v_asset_company FROM erp.asset WHERE name = NEW.asset;
    IF v_asset_company IS DISTINCT FROM NEW.company THEN
        RAISE EXCEPTION 'Asset company (%) does not match machine_context company (%)', v_asset_company, NEW.company;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_machine_context_company ON pp.machine_context;
CREATE TRIGGER trg_check_machine_context_company
    BEFORE INSERT OR UPDATE ON pp.machine_context
    FOR EACH ROW EXECUTE FUNCTION pp.check_machine_context_company_match();

CREATE OR REPLACE FUNCTION pp.check_asset_company_update()
RETURNS TRIGGER AS $$
DECLARE
    v_mc_company TEXT;
BEGIN
    IF OLD.company IS DISTINCT FROM NEW.company THEN
        SELECT company INTO v_mc_company FROM pp.machine_context WHERE asset = NEW.name;
        IF v_mc_company IS NOT NULL AND v_mc_company IS DISTINCT FROM NEW.company THEN
            RAISE EXCEPTION 'Cannot update asset company to %: matches machine_context company %', NEW.company, v_mc_company;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_asset_company_update ON erp.asset;
CREATE TRIGGER trg_check_asset_company_update
    BEFORE UPDATE ON erp.asset
    FOR EACH ROW EXECUTE FUNCTION pp.check_asset_company_update();

-- Add nullable site_id, production_line_id, station_id to pp.wo_identification_session if exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'pp' AND table_name = 'wo_identification_session') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'pp' AND table_name = 'wo_identification_session' AND column_name = 'site_id') THEN
            ALTER TABLE pp.wo_identification_session ADD COLUMN site_id TEXT REFERENCES pp.production_site(id) ON DELETE RESTRICT;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'pp' AND table_name = 'wo_identification_session' AND column_name = 'production_line_id') THEN
            ALTER TABLE pp.wo_identification_session ADD COLUMN production_line_id TEXT REFERENCES pp.production_line(id) ON DELETE RESTRICT;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'pp' AND table_name = 'wo_identification_session' AND column_name = 'station_id') THEN
            ALTER TABLE pp.wo_identification_session ADD COLUMN station_id TEXT REFERENCES pp.production_station(id) ON DELETE RESTRICT;
        END IF;
    END IF;
END $$;
