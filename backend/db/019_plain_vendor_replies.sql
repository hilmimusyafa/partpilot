-- Plain text replies belong to the single active RFQ, not every historic RFQ.
-- Explicit foreign reply references and pre-RFQ timestamps never fall back.
CREATE OR REPLACE FUNCTION pp.wa_inbound(p_transport text,p_phone text,p_body text,p_received timestamptz,p_quoted text DEFAULT NULL) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp AS $$
DECLARE v pp.wa_recipient; c pp.wa_conversation; m pp.wa_message; mid text; why text; refs text[];
BEGIN
 PERFORM pg_advisory_xact_lock_shared(72490122);
 SELECT * INTO v FROM pp.wa_recipient WHERE phone=p_phone;
 IF NOT FOUND THEN RAISE EXCEPTION 'wa_recipient_not_allowed'; END IF;
 -- Serialize repeated inbound delivery without inverting run/conversation locks.
 PERFORM pg_advisory_xact_lock(hashtextextended('wa-inbound:'||v.id,0));
 SELECT * INTO m FROM pp.wa_message WHERE transport_id=p_transport;
 IF FOUND THEN
  IF m.vendor_id<>v.id OR m.body<>p_body THEN RAISE EXCEPTION 'idempotency_conflict'; END IF;
  RETURN m.id;
 END IF;
 PERFORM 1 FROM pp.demo_run WHERE id=(SELECT run_id FROM pp.wa_conversation WHERE vendor_id=v.id AND status<>'closed') FOR UPDATE;
 SELECT * INTO c FROM pp.wa_conversation WHERE vendor_id=v.id AND status<>'closed' FOR UPDATE;
 why='active_rfq';
 IF c.id IS NULL THEN why='no_active_rfq';
 ELSIF p_received IS NULL OR p_received<c.created_at-interval '5 seconds' OR NOT EXISTS(
   SELECT 1 FROM pp.wa_message WHERE conversation_id=c.id AND kind='rfq' AND status='sent' AND delivered_at<=p_received+interval '5 seconds') THEN why='before_rfq_delivery';c.id=NULL;
 ELSIF p_quoted IS NOT NULL AND NOT EXISTS(SELECT 1 FROM pp.wa_message WHERE conversation_id=c.id AND direction='out' AND status='sent' AND transport_id=p_quoted) THEN why='different_reply_reference';c.id=NULL;
 ELSE
  FOR refs IN SELECT regexp_matches(p_body,'\mPP-([a-zA-Z0-9-]+)','gi') LOOP
   IF lower(refs[1])<>left(c.id,8) THEN why='different_text_reference';c.id=NULL;EXIT; END IF;
  END LOOP;
 END IF;
 INSERT INTO pp.wa_message(conversation_id,vendor_id,direction,kind,body,transport_id,status,received_at,payload)
 VALUES(c.id,v.id,'in','reply',p_body,p_transport,CASE WHEN c.id IS NULL THEN 'unmatched' ELSE 'received' END,LEAST(p_received,now()),
  jsonb_build_object('quoted_transport_id',p_quoted,'routing_reason',why)) RETURNING id INTO mid;
 IF c.id IS NOT NULL THEN
  UPDATE pp.wa_conversation SET last_inbound_at=GREATEST(last_inbound_at,LEAST(p_received,now())),status='partial',version=version+1 WHERE id=c.id;
  UPDATE pp.demo_run SET version=version+1 WHERE id=c.run_id;
 END IF;
 INSERT INTO pp.wa_audit(conversation_id,event_type,payload) VALUES(c.id,'inbound_received',jsonb_build_object('message_id',mid,'routing_reason',why));
 RETURN mid;
END $$;
REVOKE ALL ON FUNCTION pp.wa_inbound(text,text,text,timestamptz,text) FROM PUBLIC;
