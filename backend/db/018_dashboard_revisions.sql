-- Dashboard invalidation for incomplete/review vendor replies.
-- No outbound messages, approval or historical snapshot rewrites.
CREATE OR REPLACE FUNCTION pp.wa_apply(p_id text,p_version bigint,p_fields jsonb,p_status text,p_quote jsonb,p_message_ids jsonb) RETURNS boolean
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
  END IF;
 END IF;
 -- Every applied extraction can change eligibility, even without a complete quote.
 UPDATE pp.demo_run SET version=version+1 WHERE id=c.run_id;
 INSERT INTO pp.wa_audit(conversation_id,event_type,payload) VALUES(c.id,'extraction_applied',jsonb_build_object('status',p_status,'fields',p_fields,'message_ids',p_message_ids));
 RETURN true;
END $$;

CREATE OR REPLACE FUNCTION pp.wa_parse_attempt(p_id text) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp AS $$
DECLARE m pp.wa_message;
BEGIN
 PERFORM pg_advisory_xact_lock_shared(72490122);
 -- Same run -> conversation lock order as wa_apply/wa_enqueue.
 PERFORM 1 FROM pp.demo_run WHERE id=(SELECT c.run_id FROM pp.wa_conversation c JOIN pp.wa_message msg ON msg.conversation_id=c.id WHERE msg.id=p_id) FOR UPDATE;
 PERFORM 1 FROM pp.wa_conversation WHERE id=(SELECT conversation_id FROM pp.wa_message WHERE id=p_id) FOR UPDATE;
 SELECT * INTO m FROM pp.wa_message WHERE id=p_id FOR UPDATE;
 IF NOT FOUND OR m.direction<>'in' OR m.status<>'received' THEN RETURN false; END IF;
 IF m.parse_attempts>=2 THEN
  UPDATE pp.wa_conversation SET status='needs_review',version=version+1 WHERE id=m.conversation_id AND status<>'closed';
  IF FOUND THEN UPDATE pp.demo_run SET version=version+1 WHERE id=(SELECT run_id FROM pp.wa_conversation WHERE id=m.conversation_id); END IF;
  UPDATE pp.wa_message SET status='processed' WHERE id=m.id;
  INSERT INTO pp.wa_audit(conversation_id,event_type,payload) VALUES(m.conversation_id,'extraction_attempts_exhausted',jsonb_build_object('message_id',m.id));
  RETURN false;
 END IF;
 UPDATE pp.wa_message SET parse_attempts=parse_attempts+1 WHERE id=m.id;
 INSERT INTO pp.wa_audit(conversation_id,event_type,payload) VALUES(m.conversation_id,'extraction_attempt',jsonb_build_object('message_id',m.id,'attempt',m.parse_attempts+1));
 RETURN true;
END $$;

REVOKE ALL ON FUNCTION pp.wa_apply(text,bigint,jsonb,text,jsonb,jsonb),pp.wa_parse_attempt(text) FROM PUBLIC;
