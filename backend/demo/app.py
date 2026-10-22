"""Dedicated demo HTTP entrypoint. Password and database stay on the server."""
import base64
import hmac
import os
import psycopg
from pathlib import Path
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.staticfiles import StaticFiles
from backend.wo.app import app
from backend.wo.repository import get_db_connection,get_test_db_url
from .console import router

app.include_router(router)

@app.middleware('http')
async def demo_boundary(request:Request,call_next):
    if request.url.path == '/api/v1/health':
        return await call_next(request)
    password=os.environ.get('PARTPILOT_DEMO_PASSWORD','')
    if not password:
        return JSONResponse({'error':{'code':'demo_disabled','message':'Demo login not configured'}},503)
    try:
        scheme,encoded=request.headers.get('authorization','').split(' ',1)
        user,provided=base64.b64decode(encoded,validate=True).decode().split(':',1)
        valid=scheme.lower()=='basic' and hmac.compare_digest(user,'demo') and hmac.compare_digest(provided,password)
    except (ValueError,UnicodeError):valid=False
    if not valid:
        return JSONResponse({'error':{'code':'login_required','message':'Login demo diperlukan'}},401,headers={'WWW-Authenticate':'Basic realm="PartPilot demo", charset="UTF-8"','Cache-Control':'no-store'})
    if request.method not in ('GET','HEAD','OPTIONS'):
        allowed=os.environ.get('PARTPILOT_PUBLIC_ORIGIN','https://partpilot.rifqisetiawan.my.id')
        origin=request.headers.get('origin')
        if request.headers.get('x-partpilot-request')!='demo' or (origin and origin!=allowed):
            return JSONResponse({'error':{'code':'request_forbidden','message':'Invalid request origin or header'}},403)
    if request.url.path.startswith('/api/v1/') and request.url.path not in ('/api/v1/demo/reset','/api/v1/health'):
        try:
            async with await psycopg.AsyncConnection.connect(get_test_db_url(),connect_timeout=3) as fence:
                await fence.execute("SET LOCAL lock_timeout='5s'")
                await fence.execute('SELECT pg_advisory_xact_lock_shared(72490122)')
                cursor=await fence.execute('SELECT generation FROM pp.demo_control WHERE singleton')
                current=(await cursor.fetchone())[0]
                if request.method not in ('GET','HEAD','OPTIONS') and request.headers.get('x-partpilot-generation')!=str(current):
                    return JSONResponse({'error':{'code':'generation_conflict','message':'Demo sudah direset. Muat ulang halaman sebelum mengirim.'}},409)
                response=await call_next(request)
        except psycopg.Error:
            return JSONResponse({'error':{'code':'demo_busy','message':'Demo sedang sibuk. Coba lagi setelah memuat ulang.'}},503)
    else:
        response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='same-origin'
    response.headers['X-Frame-Options']='DENY'
    return response

@app.get('/api/v1/health')
def health():
    try:
        with get_db_connection() as conn:conn.execute('SELECT 1')
    except Exception:return JSONResponse({'status':'unavailable'},503)
    return {'status':'ok','mode':'synthetic-demo'}

static=Path(os.environ.get('PARTPILOT_STATIC_DIR',str(Path(__file__).resolve().parents[2]/'frontend-web/out')))
if static.is_dir():
    app.mount('/',StaticFiles(directory=static,html=True),name='frontend')
