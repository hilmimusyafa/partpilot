from typing import Literal

from fastapi import APIRouter

from . import service
from .models import AssessmentInput

router = APIRouter(prefix='/api/v1/maintenance', tags=['Source-backed maintenance'])


@router.get('/evidence')
def list_evidence(kind: Literal['published_case', 'catalog_part', 'troubleshooting', 'economic_case'] | None = None):
    return service.list_evidence(kind)


@router.get('/evidence/{evidence_id:path}')
def get_evidence(evidence_id: str):
    return service.get_evidence(evidence_id)


@router.post('/assess', status_code=201)
def assess(body: AssessmentInput):
    return service.assess(body)


@router.get('/assessments/{assessment_id}')
def get_assessment(assessment_id: str):
    return service.get_assessment(assessment_id)
