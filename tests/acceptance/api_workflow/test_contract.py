from helpers import BASE


def test_generated_openapi_exposes_pinned_slice(rig):
    spec = rig.app.openapi()
    operations = [
        (BASE, 'post', 'intakeWorkOrder', '202'),
        (BASE + '/{work_order_id}', 'get', 'getWorkOrder', '200'),
        (BASE + '/{work_order_id}/parts/{wo_part_id}/clarifications/answer', 'post', 'answerClarification', '202'),
        (BASE + '/{work_order_id}/parts/{wo_part_id}/match', 'post', 'matchPart', '202'),
    ]
    for path, method, operation_id, status in operations:
        operation = spec['paths'][path][method]
        assert operation['operationId'] == operation_id
        assert status in operation['responses']
        if method == 'post':
            assert 'application/json' in operation['requestBody']['content']
            assert any(p['name'].lower() == 'idempotency-key' and p['in'] == 'header' and p['required']
                       for p in operation['parameters'])
    assert not any('/resume' in p or '/decide' in p or '/worker' in p for p in spec['paths'])
