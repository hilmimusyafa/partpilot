from psycopg.types.json import Jsonb
from backend.procurement.repository import query

def call(name,*args):
    if name not in {'wa_start','wa_enqueue','wa_inbound','wa_delivery','wa_apply','wa_parse_attempt'}:raise ValueError('Unsupported function')
    values=tuple(Jsonb(x) if isinstance(x,(dict,list)) else x for x in args)
    return query(f"SELECT pp.{name}({','.join(['%s']*len(args))}) result",values)[0]['result']

def available():
    return bool(query("SELECT to_regclass('pp.wa_conversation') IS NOT NULL ready")[0]['ready'])
