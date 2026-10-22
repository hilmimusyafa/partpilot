from fastapi import APIRouter, Header
from .models import StartInput,EmptyInput,CompareInput,DecisionInput
from . import service

router=APIRouter(prefix='/api/v1/demo',tags=['Synthetic procurement'])
KEY=Header(...,alias='Idempotency-Key',min_length=1,max_length=128,pattern=r'^[!-~]+$')

@router.post('/sourcing-runs',status_code=201)
def start_run(body:StartInput,idempotency_key:str=KEY):
    return service.start(body,idempotency_key)

@router.get('/sourcing-runs/{run_id}')
def get_run(run_id:str):return service.get_run(run_id)

@router.post('/sourcing-runs/{run_id}/advance')
def advance_run(run_id:str,body:EmptyInput):return service.advance(run_id)

@router.post('/sourcing-runs/{run_id}/comparisons',status_code=201)
def compare(run_id:str,body:CompareInput,idempotency_key:str=KEY):
    from .comparison import create_comparison
    return create_comparison(run_id,body,idempotency_key)

@router.get('/comparisons/{comparison_id}')
def get_comparison(comparison_id:str):
    from .comparison import read_comparison
    return read_comparison(comparison_id)

@router.post('/comparisons/{comparison_id}/decision',status_code=201)
def choose(comparison_id:str,body:DecisionInput,idempotency_key:str=KEY):
    from .repository import call
    return call('demo_choose',comparison_id,body.expected_version,body.option_id,idempotency_key)
