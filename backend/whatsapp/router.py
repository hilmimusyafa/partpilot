from fastapi import APIRouter
from backend.procurement.models import EmptyInput
from . import service
router=APIRouter(prefix='/api/v1/whatsapp',tags=['WhatsApp demo'])

@router.get('/status')
def status():return service.status()

@router.post('/connect')
def connect(body:EmptyInput):return service.bridge('/connect',{})

@router.get('/conversations')
def conversations(run_id:str|None=None):return service.conversations(run_id)

@router.post('/runs/{run_id}/start')
def start(run_id:str,body:EmptyInput):return service.start(run_id)
