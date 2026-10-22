"""PO reads share the dedicated demo app's authentication boundary."""
from fastapi import APIRouter
from fastapi.responses import Response
from backend.procurement import repository as repo
from .pdf import render_pdf

router = APIRouter(prefix='/api/v1/demo')


def document(row):
    return dict(row['snapshot'], id=row['id'], number=row['number'],
                decision_id=row['decision_id'], run_id=row['run_id'],
                created_at=row['created_at'].isoformat(),
                pdf_url=f"/api/v1/demo/purchase-orders/{row['id']}/pdf")


@router.get('/sourcing-runs/{run_id}/purchase-order')
def purchase_order_for_run(run_id: str):
    rows = repo.query('SELECT * FROM pp.demo_purchase_order WHERE run_id=%s', (run_id,))
    return {'purchase_order': document(rows[0]) if rows else None}


@router.get('/purchase-orders/{purchase_order_id}/pdf')
def purchase_order_pdf(purchase_order_id: str):
    rows = repo.query('SELECT * FROM pp.demo_purchase_order WHERE id=%s', (purchase_order_id,))
    if not rows:
        raise repo.ProcurementError('purchase_order_not_found', 'Purchase order not found', 404)
    order = document(rows[0])
    return Response(render_pdf(order), media_type='application/pdf', headers={
        'Content-Disposition': f'attachment; filename="{order["number"]}.pdf"',
        'Cache-Control': 'no-store',
    })
