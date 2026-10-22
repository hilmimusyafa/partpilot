-- Additive real-message ledger. No FK to resettable demo_run: external messages survive reset.
CREATE TABLE IF NOT EXISTS pp.wa_recipient(
 id text PRIMARY KEY CHECK(id IN ('WA-DEMO-1','WA-DEMO-2')),
 phone text NOT NULL UNIQUE CHECK(phone ~ '^62[0-9]{8,13}$'), label text NOT NULL,
 opted_in boolean NOT NULL DEFAULT false, consent_source text,
 demo_invite_until timestamptz, destination text NOT NULL,
 CHECK(NOT opted_in OR length(consent_source)>0)
);
CREATE TABLE IF NOT EXISTS pp.wa_conversation(
 id text PRIMARY KEY DEFAULT gen_random_uuid()::text, run_id text NOT NULL,
 vendor_id text NOT NULL REFERENCES pp.wa_recipient(id), generation bigint NOT NULL,
 snapshot jsonb NOT NULL, fields jsonb NOT NULL DEFAULT '{}',
 status text NOT NULL DEFAULT 'waiting' CHECK(status IN ('waiting','partial','quoted','no_stock','insufficient_stock','negotiation_refused','needs_review','no_response','closed')),
 last_inbound_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(),
 version bigint NOT NULL DEFAULT 1, UNIQUE(run_id,vendor_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS wa_one_live_recipient ON pp.wa_conversation(vendor_id) WHERE status<>'closed';
CREATE TABLE IF NOT EXISTS pp.wa_message(
 id text PRIMARY KEY DEFAULT gen_random_uuid()::text, conversation_id text REFERENCES pp.wa_conversation(id),
 vendor_id text NOT NULL REFERENCES pp.wa_recipient(id), direction text NOT NULL CHECK(direction IN ('in','out')),
 kind text NOT NULL CHECK(kind IN ('rfq','followup','price_counteroffer','reply')),
 body text NOT NULL CHECK(length(body) BETWEEN 1 AND 8000), payload jsonb NOT NULL DEFAULT '{}',
 request_key text, transport_id text UNIQUE,
 status text NOT NULL CHECK(status IN ('queued','sending','sent','uncertain','cancelled','received','processed','unmatched')),
 created_at timestamptz NOT NULL DEFAULT now(), received_at timestamptz, delivered_at timestamptz,
 parse_attempts integer NOT NULL DEFAULT 0 CHECK(parse_attempts BETWEEN 0 AND 2),
 UNIQUE(conversation_id,request_key)
);
CREATE UNIQUE INDEX IF NOT EXISTS wa_one_counteroffer ON pp.wa_message(conversation_id,kind) WHERE kind IN ('rfq','price_counteroffer');
CREATE TABLE IF NOT EXISTS pp.wa_audit(id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,conversation_id text,event_type text NOT NULL,payload jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT now());
CREATE TRIGGER wa_audit_immutable BEFORE UPDATE OR DELETE ON pp.wa_audit FOR EACH ROW EXECUTE FUNCTION pp.demo_immutable();

ALTER TABLE pp.demo_outbox DROP CONSTRAINT demo_outbox_vendor_id_check;
ALTER TABLE pp.demo_outbox ADD CHECK(vendor_id IN ('SIM-ENOUGH','SIM-SHORT','SIM-REFUSE','SIM-REVISE','SIM-SILENT','WA-DEMO-1','WA-DEMO-2'));

CREATE FUNCTION pp.wa_start(p_run text,p_vendor text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp AS $$
DECLARE r pp.demo_run; v pp.wa_recipient; c pp.wa_conversation; g bigint;
BEGIN
 PERFORM pg_advisory_xact_lock_shared(72490122);
 SELECT * INTO r FROM pp.demo_run WHERE id=p_run FOR UPDATE;
 IF NOT FOUND OR r.snapshot->>'status'<>'sourcing' OR EXISTS(SELECT 1 FROM pp.demo_decision WHERE run_id=p_run) THEN RAISE EXCEPTION 'run_not_sourcing'; END IF;
 SELECT * INTO v FROM pp.wa_recipient WHERE id=p_vendor FOR UPDATE;
 IF NOT FOUND OR NOT v.opted_in OR v.demo_invite_until IS NULL OR v.demo_invite_until<=now() THEN RAISE EXCEPTION 'wa_consent_or_window_required'; END IF;
 SELECT * INTO c FROM pp.wa_conversation WHERE run_id=p_run AND vendor_id=p_vendor;
 IF FOUND THEN RETURN to_jsonb(c); END IF;
 IF EXISTS(SELECT 1 FROM pp.demo_outbox WHERE run_id=p_run AND vendor_id LIKE 'SIM-%') THEN RAISE EXCEPTION 'wa_simulator_already_started'; END IF;
 SELECT generation INTO g FROM pp.demo_control WHERE singleton;
 INSERT INTO pp.wa_conversation(run_id,vendor_id,generation,snapshot) VALUES(p_run,p_vendor,g,r.snapshot||jsonb_build_object('shipping_destination',v.destination,'requires_reply_reference',EXISTS(SELECT 1 FROM pp.wa_conversation WHERE vendor_id=p_vendor))) RETURNING * INTO c;
 INSERT INTO pp.demo_outbox(run_id,vendor_id,kind,payload) VALUES(p_run,p_vendor,'rfq',r.snapshot-'availability'-'context');
 UPDATE pp.demo_run SET version=version+1 WHERE id=p_run;
 INSERT INTO pp.wa_audit(conversation_id,event_type,payload) VALUES(c.id,'conversation_started',jsonb_build_object('run_id',p_run,'consent_source',v.consent_source));
 RETURN to_jsonb(c);
END $$;

CREATE FUNCTION pp.wa_enqueue(p_conversation text,p_kind text,p_body text,p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp AS $$
DECLARE c pp.wa_conversation; v pp.wa_recipient; m pp.wa_message; k text;
BEGIN
 PERFORM 1 FROM pp.demo_run WHERE id=(SELECT run_id FROM pp.wa_conversation WHERE id=p_conversation) FOR UPDATE;
 SELECT * INTO c FROM pp.wa_conversation WHERE id=p_conversation FOR UPDATE;
 IF NOT FOUND OR c.status='closed' OR c.generation<>(SELECT generation FROM pp.demo_control WHERE singleton) OR EXISTS(SELECT 1 FROM pp.demo_decision WHERE run_id=c.run_id) THEN RAISE EXCEPTION 'wa_conversation_closed'; END IF;
 k=CASE WHEN p_kind='followup' THEN 'followup:'||(p_payload->>'request_key') ELSE p_kind END;
 SELECT * INTO m FROM pp.wa_message WHERE conversation_id=c.id AND request_key=k;
 IF FOUND THEN
  IF m.body<>p_body OR m.payload<>p_payload THEN RAISE EXCEPTION 'idempotency_conflict'; END IF;
  RETURN to_jsonb(m);
 END IF;
 SELECT * INTO v FROM pp.wa_recipient WHERE id=c.vendor_id;
 IF NOT v.opted_in OR NOT (COALESCE(c.last_inbound_at+interval '24 hours',v.demo_invite_until)>now()) THEN RAISE EXCEPTION 'wa_consent_or_window_required'; END IF;
 IF (c.snapshot->>'expires_at')::timestamptz<=now() THEN RAISE EXCEPTION 'wa_quote_window_expired'; END IF;
 IF p_kind NOT IN ('rfq','followup','price_counteroffer') OR p_payload-ARRAY['request_key','missing_fields','target_unit_price']<>'{}'::jsonb THEN RAISE EXCEPTION 'unsafe_outbound_payload'; END IF;
 IF p_kind='followup' AND (k IS NULL OR (SELECT count(*) FROM pp.wa_message WHERE conversation_id=c.id AND kind='followup')>=3 OR c.last_inbound_at IS NULL) THEN RAISE EXCEPTION 'wa_followup_limit'; END IF;
 IF p_kind='price_counteroffer' AND (c.status<>'quoted' OR NOT (c.fields ?& ARRAY['identity','qty_available','unit_price','shipping_amount','tax_amount','processing_hours','delivered_eta','valid_until']) OR
   (c.fields->>'qty_available')::numeric<(c.snapshot->>'quantity')::numeric OR
   (c.fields->>'valid_until')::timestamptz<=now() OR
   p_payload->>'target_unit_price' IS NULL OR (p_payload->>'target_unit_price')::numeric<0 OR (p_payload->>'target_unit_price')::numeric>=(c.fields->>'unit_price')::numeric) THEN RAISE EXCEPTION 'counteroffer_ineligible'; END IF;
 INSERT INTO pp.wa_message(conversation_id,vendor_id,direction,kind,body,payload,request_key,status) VALUES(c.id,c.vendor_id,'out',p_kind,p_body,p_payload,k,'queued') RETURNING * INTO m;
 IF p_kind='price_counteroffer' THEN
  INSERT INTO pp.demo_outbox(run_id,vendor_id,kind,payload) VALUES(c.run_id,c.vendor_id,p_kind,p_payload);
  UPDATE pp.demo_run SET version=version+1 WHERE id=c.run_id;
 END IF;
 INSERT INTO pp.wa_audit(conversation_id,event_type,payload) VALUES(c.id,'outbound_reserved',jsonb_build_object('message_id',m.id,'kind',p_kind));
 RETURN to_jsonb(m);
END $$;

CREATE FUNCTION pp.wa_inbound(p_transport text,p_phone text,p_body text,p_received timestamptz,p_quoted text DEFAULT NULL) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp AS $$
DECLARE v pp.wa_recipient; c pp.wa_conversation; m pp.wa_message; mid text;
BEGIN
 SELECT * INTO v FROM pp.wa_recipient WHERE phone=p_phone FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'wa_recipient_not_allowed'; END IF;
 SELECT * INTO m FROM pp.wa_message WHERE transport_id=p_transport;
 IF FOUND THEN
  IF m.vendor_id<>v.id OR m.body<>p_body THEN RAISE EXCEPTION 'idempotency_conflict'; END IF;
  RETURN m.id;
 END IF;
 SELECT * INTO c FROM pp.wa_conversation WHERE vendor_id=v.id AND status<>'closed' FOR UPDATE;
 -- Old pre-run offline messages cannot be assigned to a new RFQ.
 IF c.id IS NOT NULL AND (p_received<c.created_at-interval '5 seconds' OR NOT EXISTS(
   SELECT 1 FROM pp.wa_message WHERE conversation_id=c.id AND kind='rfq' AND status='sent' AND delivered_at<=p_received+interval '5 seconds')) THEN c.id=NULL; END IF;
 IF p_quoted IS NOT NULL AND NOT EXISTS(SELECT 1 FROM pp.wa_message WHERE conversation_id=c.id AND direction='out' AND transport_id=p_quoted) THEN c.id=NULL; END IF;
 IF c.id IS NOT NULL AND COALESCE((c.snapshot->>'requires_reply_reference')::boolean,false) AND p_quoted IS NULL AND position('PP-'||left(c.id,8) in p_body)=0 THEN c.id=NULL; END IF;
 INSERT INTO pp.wa_message(conversation_id,vendor_id,direction,kind,body,transport_id,status,received_at)
 VALUES(c.id,v.id,'in','reply',p_body,p_transport,CASE WHEN c.id IS NULL THEN 'unmatched' ELSE 'received' END,LEAST(p_received,now())) RETURNING id INTO mid;
 IF c.id IS NOT NULL THEN UPDATE pp.wa_conversation SET last_inbound_at=GREATEST(last_inbound_at,LEAST(p_received,now())),version=version+1 WHERE id=c.id; END IF;
 INSERT INTO pp.wa_audit(conversation_id,event_type,payload) VALUES(c.id,'inbound_received',jsonb_build_object('message_id',mid));
 RETURN mid;
END $$;

CREATE FUNCTION pp.wa_delivery(p_id text,p_status text,p_transport text DEFAULT NULL) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp AS $$
DECLARE m pp.wa_message; c pp.wa_conversation; v pp.wa_recipient;
BEGIN
 SELECT * INTO m FROM pp.wa_message WHERE id=p_id FOR UPDATE;
 IF NOT FOUND OR m.direction<>'out' THEN RAISE EXCEPTION 'wa_message_not_found'; END IF;
 SELECT * INTO c FROM pp.wa_conversation WHERE id=m.conversation_id;
 SELECT * INTO v FROM pp.wa_recipient WHERE id=m.vendor_id;
 IF p_status='sending' THEN
  IF m.status<>'queued' THEN RETURN to_jsonb(m); END IF;
  IF c.status='closed' OR NOT v.opted_in OR NOT COALESCE(c.last_inbound_at+interval '24 hours',v.demo_invite_until)>now() OR c.generation<>(SELECT generation FROM pp.demo_control WHERE singleton) THEN
   UPDATE pp.wa_message SET status='cancelled' WHERE id=m.id RETURNING * INTO m;
   RETURN to_jsonb(m);
  END IF;
 ELSIF p_status NOT IN ('sent','uncertain') OR m.status NOT IN ('sending','uncertain') THEN RAISE EXCEPTION 'wa_invalid_delivery_transition'; END IF;
 UPDATE pp.wa_message SET status=p_status,transport_id=COALESCE(p_transport,transport_id),delivered_at=CASE WHEN p_status='sent' THEN now() ELSE delivered_at END WHERE id=m.id RETURNING * INTO m;
 INSERT INTO pp.wa_audit(conversation_id,event_type,payload) VALUES(c.id,'delivery_'||p_status,jsonb_build_object('message_id',m.id));
 RETURN to_jsonb(m);
END $$;

CREATE FUNCTION pp.wa_apply(p_id text,p_version bigint,p_fields jsonb,p_status text,p_quote jsonb,p_message_ids jsonb) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp AS $$
DECLARE c pp.wa_conversation; q jsonb; e pp.demo_outbox;
BEGIN
 PERFORM pg_advisory_xact_lock_shared(72490122);
 PERFORM 1 FROM pp.demo_run WHERE id=(SELECT run_id FROM pp.wa_conversation WHERE id=p_id) FOR UPDATE;
 SELECT * INTO c FROM pp.wa_conversation WHERE id=p_id FOR UPDATE;
 IF NOT FOUND OR c.status='closed' OR c.version<>p_version THEN RETURN false; END IF;
 IF p_fields-ARRAY['identity','qty_available','unit_price','shipping_amount','tax_amount','processing_hours','delivered_eta','valid_until']<>'{}'::jsonb OR p_status NOT IN ('partial','quoted','no_stock','insufficient_stock','negotiation_refused','needs_review','no_response') THEN RAISE EXCEPTION 'wa_invalid_extraction'; END IF;
 IF EXISTS(SELECT 1 FROM jsonb_array_elements_text(p_message_ids) x WHERE NOT EXISTS(SELECT 1 FROM pp.wa_message m WHERE m.id=x.value AND m.conversation_id=c.id AND m.direction='in')) THEN RAISE EXCEPTION 'wa_invalid_extraction'; END IF;
 IF p_quote IS NOT NULL THEN
  IF p_quote->'identity' IS DISTINCT FROM c.snapshot->'identity' OR
   NOT (p_quote ?& ARRAY['qty_available','unit_price','shipping_amount','tax_amount','processing_hours','delivered_eta','valid_until']) OR
   p_quote->>'source' IS DISTINCT FROM 'whatsapp:vendor-reply' OR
   (p_quote->>'qty_available')::numeric<0 OR (p_quote->>'unit_price')::numeric<0 OR
   (p_quote->>'shipping_amount')::numeric<0 OR (p_quote->>'tax_amount')::numeric<0 OR (p_quote->>'processing_hours')::numeric<0 OR
   p_quote->>'destination_warehouse_id' IS DISTINCT FROM c.snapshot->>'destination_warehouse_id' THEN RAISE EXCEPTION 'invalid_vendor_response'; END IF;
 END IF;
 UPDATE pp.wa_conversation SET fields=p_fields,status=p_status,version=version+1 WHERE id=c.id;
 UPDATE pp.wa_message SET status='processed' WHERE id IN (SELECT jsonb_array_elements_text(p_message_ids)) AND status='received';
 -- Publication shares existing comparison/manager DB guards and revisions invalidate old comparisons.
 IF p_quote IS NOT NULL OR p_status IN ('no_stock','no_response','negotiation_refused') THEN
  SELECT * INTO e FROM pp.demo_outbox WHERE run_id=c.run_id AND vendor_id=c.vendor_id AND (kind='rfq' OR EXISTS(
    SELECT 1 FROM pp.wa_message outbound JOIN pp.wa_message inbound ON inbound.conversation_id=outbound.conversation_id
     WHERE outbound.conversation_id=c.id AND outbound.kind='price_counteroffer' AND outbound.status='sent'
      AND inbound.id IN (SELECT jsonb_array_elements_text(p_message_ids)) AND inbound.received_at>=outbound.delivered_at-interval '5 seconds'))
   ORDER BY CASE kind WHEN 'price_counteroffer' THEN 0 ELSE 1 END LIMIT 1 FOR UPDATE;
  IF FOUND THEN
   q=jsonb_build_object('event_id',e.id,'run_id',c.run_id,'vendor_id',c.vendor_id,'outcome',CASE WHEN p_status='insufficient_stock' THEN 'quoted' WHEN p_status='quoted' AND e.kind='price_counteroffer' THEN 'revised_quote' ELSE p_status END,'quote',p_quote);
   UPDATE pp.demo_outbox SET response=q WHERE id=e.id;
   UPDATE pp.demo_run SET version=version+1 WHERE id=c.run_id;
  END IF;
 END IF;
 INSERT INTO pp.wa_audit(conversation_id,event_type,payload) VALUES(c.id,'extraction_applied',jsonb_build_object('status',p_status,'fields',p_fields,'message_ids',p_message_ids));
 RETURN true;
END $$;

CREATE FUNCTION pp.wa_parse_attempt(p_id text) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp AS $$
DECLARE m pp.wa_message;
BEGIN
 PERFORM 1 FROM pp.wa_conversation WHERE id=(SELECT conversation_id FROM pp.wa_message WHERE id=p_id) FOR UPDATE;
 SELECT * INTO m FROM pp.wa_message WHERE id=p_id FOR UPDATE;
 IF NOT FOUND OR m.direction<>'in' OR m.status<>'received' THEN RETURN false; END IF;
 IF m.parse_attempts>=2 THEN
  UPDATE pp.wa_conversation SET status='needs_review',version=version+1 WHERE id=m.conversation_id AND status<>'closed';
  UPDATE pp.wa_message SET status='processed' WHERE id=m.id;
  INSERT INTO pp.wa_audit(conversation_id,event_type,payload) VALUES(m.conversation_id,'extraction_attempts_exhausted',jsonb_build_object('message_id',m.id));
  RETURN false;
 END IF;
 UPDATE pp.wa_message SET parse_attempts=parse_attempts+1 WHERE id=m.id;
 INSERT INTO pp.wa_audit(conversation_id,event_type,payload) VALUES(m.conversation_id,'extraction_attempt',jsonb_build_object('message_id',m.id,'attempt',m.parse_attempts+1));
 RETURN true;
END $$;

CREATE FUNCTION pp.wa_cancel_on_reset() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp AS $$
BEGIN
 INSERT INTO pp.wa_audit(conversation_id,event_type,payload) SELECT id,'closed_by_demo_reset',jsonb_build_object('run_id',run_id) FROM pp.wa_conversation WHERE status<>'closed';
 UPDATE pp.wa_conversation SET status='closed',version=version+1 WHERE status<>'closed';
 UPDATE pp.wa_message SET status='cancelled' WHERE direction='out' AND status='queued';
 RETURN NULL;
END $$;
CREATE TRIGGER wa_preserve_external_history BEFORE TRUNCATE ON pp.demo_run FOR EACH STATEMENT EXECUTE FUNCTION pp.wa_cancel_on_reset();

CREATE FUNCTION pp.wa_assert_current_quote(p_run text,p_vendor text,p_quote jsonb) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp AS $$
DECLARE c pp.wa_conversation;
BEGIN
 SELECT * INTO c FROM pp.wa_conversation WHERE run_id=p_run AND vendor_id=p_vendor FOR UPDATE;
 IF NOT FOUND OR c.status NOT IN ('quoted','negotiation_refused') OR
  (c.fields-ARRAY['delivered_eta','valid_until']) IS DISTINCT FROM (p_quote-ARRAY['quote_id','revision','quantity_unit','currency','destination_warehouse_id','source','assumption_version','delivered_eta','valid_until']) OR
  (c.fields->>'delivered_eta')::timestamptz IS DISTINCT FROM (p_quote->>'delivered_eta')::timestamptz OR
  (c.fields->>'valid_until')::timestamptz IS DISTINCT FROM (p_quote->>'valid_until')::timestamptz OR
  EXISTS(SELECT 1 FROM pp.demo_outbox WHERE run_id=p_run AND vendor_id=p_vendor AND kind='price_counteroffer' AND response IS NULL)
 THEN RAISE EXCEPTION 'quote_changed'; END IF;
END $$;
CREATE FUNCTION pp.wa_guard_comparison() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp AS $$
DECLARE opt jsonb;
BEGIN
 FOR opt IN SELECT value FROM jsonb_array_elements(NEW.snapshot->'eligible_complete_options') LOOP
  IF opt->>'source_kind'='vendor' AND opt->>'source_id' LIKE 'WA-%' THEN
   PERFORM pp.wa_assert_current_quote(NEW.run_id,opt->>'source_id',opt->'quote');
  END IF;
 END LOOP;
 RETURN NEW;
END $$;
CREATE FUNCTION pp.wa_guard_decision() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp AS $$
DECLARE opt jsonb;
BEGIN
 SELECT value INTO opt FROM pp.demo_comparison c CROSS JOIN LATERAL jsonb_array_elements(c.snapshot->'eligible_complete_options') WHERE c.id=NEW.comparison_id AND value->>'option_id'=NEW.option_id;
 IF opt->>'source_kind'='vendor' AND opt->>'source_id' LIKE 'WA-%' THEN PERFORM pp.wa_assert_current_quote(NEW.run_id,opt->>'source_id',opt->'quote'); END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER wa_revalidate_comparison BEFORE INSERT ON pp.demo_comparison FOR EACH ROW EXECUTE FUNCTION pp.wa_guard_comparison();
CREATE TRIGGER wa_revalidate_decision BEFORE INSERT ON pp.demo_decision FOR EACH ROW EXECUTE FUNCTION pp.wa_guard_decision();

REVOKE ALL ON pp.wa_recipient,pp.wa_conversation,pp.wa_message,pp.wa_audit FROM PUBLIC;
REVOKE ALL ON FUNCTION pp.wa_start(text,text),pp.wa_enqueue(text,text,text,jsonb),pp.wa_inbound(text,text,text,timestamptz,text),pp.wa_delivery(text,text,text),pp.wa_apply(text,bigint,jsonb,text,jsonb,jsonb),pp.wa_cancel_on_reset(),pp.wa_parse_attempt(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION pp.wa_assert_current_quote(text,text,jsonb),pp.wa_guard_comparison(),pp.wa_guard_decision() FROM PUBLIC;
