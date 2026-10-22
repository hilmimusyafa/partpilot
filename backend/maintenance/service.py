from .agent import assess
from .repository import MaintenanceError, PostgresStore


def get_assessment(assessment_id):
    return PostgresStore().get_assessment(assessment_id)


def list_evidence(kind=None):
    return {'items': PostgresStore().list_evidence(kind),
            'scope': 'external_published_OEM_evidence_not_local_asset_history'}


def get_evidence(evidence_id):
    row = PostgresStore().get_evidence(evidence_id)
    if row is None:
        raise MaintenanceError('evidence_not_found', 'Evidence not found', 404)
    return row
