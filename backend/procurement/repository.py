"""Only validating DB functions write procurement state; each records an audit event."""
from psycopg import Error
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
import json
from datetime import datetime
from backend.wo.repository import get_db_connection, RepositoryError

class ProcurementError(RepositoryError):
    def __init__(self,code,message,status_code=409):
        super().__init__(code,message,status_code)

def query(sql,params=()):
    try:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql,params)
                return cur.fetchall() if cur.description else []
    except Error as exc:
        # No raw DB diagnostics/DSN in HTTP responses.
        msg=str(exc).split('\n')[0]
        allowed={'idempotency_conflict','version_conflict','identity_or_version_conflict','run_not_found',
                 'counteroffer_or_request_conflict','run_not_sourcing','unsafe_outbound_payload',
                 'counteroffer_ineligible','response_conflict','invalid_vendor_response','decision_conflict',
                 'option_ineligible_or_expired','quote_changed','stock_changed','comparison_not_found',
                 'invalid_source_snapshot','invalid_comparison','item_changed','run_already_exists','unsupported_source_unit','reset_disabled','reset_confirmation_required','generation_conflict','demo_busy'}
        allowed.update({'wa_consent_or_window_required','wa_simulator_already_started','wa_conversation_closed','wa_quote_window_expired','wa_followup_limit','wa_recipient_not_allowed','wa_message_not_found','wa_invalid_delivery_transition','wa_invalid_extraction'})
        allowed.add('negotiation_plan_mismatch')
        code=msg if msg in allowed else 'procurement_storage_error'
        raise ProcurementError(code,code,409 if code in allowed else 503) from None

def call(name,*args):
    allowed={'demo_start','demo_enqueue','demo_receive','demo_compare','demo_choose','demo_plan_negotiation'}
    if name not in allowed:raise ValueError('unsupported database function')
    def encode(value):
        return json.dumps(value,default=lambda v:v.isoformat() if isinstance(v,datetime) else str(v))
    args=tuple(Jsonb(x,dumps=encode) if isinstance(x,dict) else x for x in args)
    return query(f"SELECT pp.{name}({','.join(['%s']*len(args))}) AS result",args)[0]['result']

def run_row(run_id):
    rows=query('SELECT * FROM pp.demo_run WHERE id=%s',(run_id,))
    if not rows:raise ProcurementError('run_not_found','Run not found',404)
    return rows[0]

def exchanges(run_id):
    return query('SELECT * FROM pp.demo_outbox WHERE run_id=%s ORDER BY vendor_id,created_at,id',(run_id,))

def comparison_row(cid):
    rows=query('SELECT * FROM pp.demo_comparison WHERE id=%s',(cid,))
    if not rows:raise ProcurementError('comparison_not_found','Comparison not found',404)
    return rows[0]
