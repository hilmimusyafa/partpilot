"""Portable schedule regression: late eligible vendors must include full recovery."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from backend.wo.economics import evaluate_schedule
from backend.wo.models import RestoreSchedule


def source(start, ident, arrival_hours, *, reasons=None, expired=False):
    return dict(source_id=ident, reasons=reasons or [], quote=dict(
        delivered_eta=(start + timedelta(hours=arrival_hours)).isoformat(),
        valid_until=(start + timedelta(hours=-1 if expired else 24)).isoformat()))


def test_common_horizon_includes_late_vendor_installation_and_restart():
    from backend.demo.food import recovery_options
    start = datetime(2026, 10, 23, tzinfo=timezone.utc)
    options = recovery_options([
        source(start, 'warehouse', 4),
        source(start, 'late-vendor', 96),
        source(start, 'insufficient-vendor', 240, reasons=['insufficient_stock']),
        source(start, 'expired-vendor', 300, expired=True),
    ], start)
    assert {o['schedule']['horizon_end'] for o in options} == {'2026-10-27T02:00:00+00:00'}
    fast, late = [RestoreSchedule.model_validate(o['schedule']) for o in options[:2]]
    assert evaluate_schedule(fast)[:2] == (Decimal('6'), Decimal('6'))
    assert evaluate_schedule(late)[:2] == (Decimal('98'), Decimal('98'))
    assert all(o['schedule']['calendar_source'] == 'synthetic:continuous production; full stop' for o in options)
    assert all(o['schedule']['scheduled_impacted_windows'] == [
        {'start': start.isoformat(), 'end': '2026-10-27T02:00:00+00:00'}] for o in options)


def test_short_options_keep_minimum_48_hour_common_horizon():
    from backend.demo.food import recovery_options
    start = datetime(2026, 10, 23, tzinfo=timezone.utc)
    options = recovery_options([source(start, 'warehouse', 4), source(start, 'vendor', 8)], start)
    assert {o['schedule']['horizon_end'] for o in options} == {'2026-10-25T00:00:00+00:00'}
    assert evaluate_schedule(RestoreSchedule.model_validate(options[1]['schedule']))[:2] == (Decimal('10'), Decimal('10'))
