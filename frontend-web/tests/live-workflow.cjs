/* eslint-disable @typescript-eslint/no-require-imports -- Standalone CommonJS browser tests. */
const assert = require('node:assert/strict');
const path = require('node:path');

async function testLiveWorkflow(browser, url, fixture, artifacts) {
  const { config, baseSession, baseRun, quote, option } = fixture;
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  page.setDefaultTimeout(10000);
  await page.clock.install();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  let version = 1, decision = null, prepareFailures = 0, listReads = 0, decisionWrites = 0, chatFailure = false, preflightChange = false, missingVersionOnce = false;
  const prepares = [];
  const snapshots = new Map();
  const complete = () => version !== 1 && version !== 3;
  const currentQuote = () => ({ ...quote, unit_price: version >= 5 ? '17000' : version >= 4 ? '15000' : '10000' });
  function liveRun() {
    return { ...baseRun, transport: 'whatsapp', version, negotiation: null, decision,
      vendors: [{ vendor_id: 'WA-VENDOR', outcome: version === 1 ? 'partial' : 'quoted', quote: currentQuote(), initial_quote: quote, counteroffers_used: version >= 3 ? 1 : 0, eligible: complete(), ineligible_reasons: complete() ? [] : version === 3 ? ['negotiation_pending'] : ['missing_shipping_amount'] }] };
  }
  function snapshot() {
    const warehouse = { ...option('SYN-WH-02', 'warehouse', 300000), option_id: 'warehouse:SYN-WH-02' };
    const vendor = { ...option('WA-VENDOR', 'vendor', 200000 + version), option_id: 'vendor:WA-VENDOR', quote: currentQuote() };
    const value = { id: `live-${version}`, version: 1, source_run_version: version, eligible_complete_options: complete() ? [warehouse, vendor] : [warehouse], unrankable_options: complete() ? [] : [{ ...vendor, reasons: version === 3 ? ['negotiation_pending'] : ['no_valid_quote'] }], unexpired_option_ids: complete() ? [warehouse.option_id, vendor.option_id] : [warehouse.option_id], coverage_complete: complete() };
    snapshots.set(value.id, value); return value;
  }
  snapshot();
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const endpoint = new URL(request.url()).pathname.replace('/api/v1', '');
    let payload;
    if (request.method() === 'POST') {
      if (endpoint === '/demo/sourcing-runs/run/prepare-comparison') {
        prepares.push(request.headers()['idempotency-key']);
        if (prepareFailures > 0) { prepareFailures--; return route.fulfill({ status: 409, json: { error: { code: 'version_conflict', message: 'Data penawaran sedang berubah.' } } }); }
        payload = snapshot();
      } else if (/^\/demo\/comparisons\/live-\d+\/decision$/.test(endpoint)) {
        assert.equal(endpoint, `/demo/comparisons/live-${version}/decision`, 'Approval must use the reviewed fresh comparison');
        decisionWrites++; decision = { option_id: request.postDataJSON().option_id, comparison_id: `live-${version}` }; payload = decision;
      } else throw new Error(`Forbidden live fixture write: ${endpoint}`);
    } else if (endpoint === '/demo/config') payload = config;
    else if (endpoint === '/demo/orders/session') payload = { ...baseSession, comparison_id: `live-${version}`, decision };
    else if (endpoint === '/demo/orders') { listReads++; payload = { generation: 1, items: [] }; }
    else if (endpoint === '/demo/sourcing-runs/run') { if (preflightChange) { version++; preflightChange = false; } payload = liveRun(); }
    else if (endpoint.startsWith('/demo/comparisons/')) {
      payload = snapshots.get(endpoint.split('/').at(-1));
      if (missingVersionOnce) { missingVersionOnce = false; payload = { ...payload, source_run_version: undefined }; }
    }
    else if (endpoint === '/whatsapp/status') payload = { connection: 'connected', can_start: true, recipients: [] };
    else if (endpoint === '/whatsapp/conversations') {
      if (chatFailure) { chatFailure = false; return route.fulfill({ status: 503, json: { error: { message: 'Chat temporarily unavailable' } } }); }
      payload = { conversations: [{ id: 'unmatched-active', run_id: 'run', vendor_id: 'WA-UNMATCHED', status: 'no_stock', fields: {}, missing_fields: ['unit_price'], messages: [], unmatched_messages: [{ direction: 'in', text: 'Penawaran lama belum terhubung', created_at: '2025-01-01T00:00:00Z', routing_reason: 'ambiguous' }], followups_used: 0, counteroffers_used: 0 }, { id: 'closed-history', run_id: 'run', vendor_id: 'WA-OLD', status: 'closed', fields: {}, missing_fields: [], messages: [{ direction: 'in', text: 'Balasan lama', created_at: '2025-01-01T00:00:00Z' }], followups_used: 0, counteroffers_used: 0 }] };
    } else if (endpoint === '/demo/sourcing-runs/run/purchase-order') payload = { purchase_order: decision?.option_id.startsWith('vendor:') ? { id: 'live-po', number: 'LIVE-MOCK-PO', quantity: '6', total: '109000' } : null };
    else throw new Error(`Unexpected live fixture API: ${endpoint}`);
    assert(payload !== undefined, `Missing fixture ${endpoint}`);
    await route.fulfill({ json: payload });
  });
  try {
    await page.goto(`${url}/manager/decision/?session=session`);
    const vendors = page.getByRole('region', { name: 'Penawaran vendor', exact: true });
    await vendors.getByText('Belum dapat dipilih', { exact: true }).waitFor();
    await page.getByText('Percakapan ini sudah ditutup.', { exact: false }).waitFor();
    const unmatched = page.locator('#conversation-unmatched-active');
    await unmatched.getByText('Pesan diterima, tetapi belum terhubung ke permintaan ini').waitFor();
    await unmatched.getByText('Penawaran lama belum terhubung', { exact: true }).waitFor();
    assert.equal(await unmatched.getByText(/Belum lengkap:/).count(), 0, 'No-stock result must not demand quote completion');
    await page.clock.runFor(5100);
    assert.equal(prepares.length, 0, 'Unchanged version must not continually create comparisons');
    missingVersionOnce = true;
    await page.clock.runFor(5100);
    await page.getByText(/Versi penawaran pada perbandingan belum tersedia/).waitFor();
    version = 2; prepareFailures = 1;
    await page.clock.runFor(5100);
    await page.getByText(/Pembaruan otomatis tertunda/).waitFor();
    chatFailure = true;
    await page.clock.runFor(5100);
    await vendors.getByRole('button', { name: 'Setujui PO', exact: true }).waitFor();
    assert.deepEqual(prepares, ['comparison-run-2', 'comparison-run-2']);
    assert.match(await vendors.innerText(), /#1 global/);
    assert.equal(listReads, 0, 'Decision must read the current WO directly, even when absent from the 100-item list');
    await vendors.getByRole('button', { name: 'Setujui PO', exact: true }).click();
    version = 3;
    await page.clock.runFor(5100);
    await page.getByRole('button', { name: 'Tutup & perbarui', exact: true }).waitFor();
    assert.equal(await page.getByRole('button', { name: 'Konfirmasi PO demo', exact: true }).isDisabled(), true);
    assert.equal(prepares.length, 2, 'An open confirmation must retain its comparison snapshot');
    await page.getByRole('button', { name: 'Tutup & perbarui', exact: true }).click();
    await vendors.getByText(/Menunggu jawaban negosiasi/).waitFor();
    assert.equal(await vendors.getByRole('button', { name: 'Setujui PO', exact: true }).count(), 0);
    version = 4;
    await page.clock.runFor(5100);
    await vendors.getByRole('button', { name: 'Setujui PO', exact: true }).waitFor();
    assert.match(await vendors.innerText(), /15[.]000/);
    await vendors.getByRole('button', { name: 'Setujui PO', exact: true }).click();
    preflightChange = true;
    await page.getByRole('button', { name: 'Konfirmasi PO demo', exact: true }).click();
    await page.getByRole('button', { name: 'Tutup & perbarui', exact: true }).waitFor();
    assert.equal(decisionWrites, 0, 'Preflight run change must prevent stale approval');
    await page.getByRole('button', { name: 'Tutup & perbarui', exact: true }).click();
    await vendors.getByText(/17[.]000/).waitFor();
    await vendors.getByRole('button', { name: 'Setujui PO', exact: true }).click();
    await page.getByRole('button', { name: 'Konfirmasi PO demo', exact: true }).click();
    await page.getByRole('link', { name: 'Unduh PO (PDF)' }).waitFor();
    assert.equal(decisionWrites, 1);
    const preparedAtSelection = prepares.length;
    version++;
    await page.clock.runFor(5100);
    assert.equal(prepares.length, preparedAtSelection, 'A recorded selection must stop automatic comparison creation');
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(artifacts, 'live-auto-comparison.png'), fullPage: true });
    // Another tab's committed decision must become visible without an approval write here.
    decision = null; snapshot();
    await page.reload();
    await vendors.getByRole('button', { name: 'Setujui PO', exact: true }).waitFor();
    await vendors.getByRole('button', { name: 'Setujui PO', exact: true }).click();
    decision = { option_id: 'vendor:WA-VENDOR', comparison_id: `live-${version}` };
    await page.clock.runFor(5100);
    await page.getByRole('link', { name: 'Unduh PO (PDF)' }).waitFor();
    assert.equal(await page.getByRole('button', { name: 'Konfirmasi PO demo', exact: true }).isDisabled(), true);
    assert.equal(decisionWrites, 1);
    assert.deepEqual(errors, []);
    console.log('PASS: automatic live comparison, conflict retry, independent chat failure, pending-again quote, pinned/stale modal, approval preflight race, no refresh loop, other-tab decision, closed chat history.');
  } finally { await context.close(); }
}

async function testWoLifecycle(browser, url, fixture, artifacts) {
  const { config, baseSession, baseRun } = fixture;
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  page.setDefaultTimeout(10000);
  await page.clock.install();
  let session = { ...baseSession, id: 'created-wo', version: 1, state: 'draft', run_id: null, comparison_id: null };
  let submitFailure = true, orderReadFailure = false, submits = 0;
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/api/v1/**', async route => {
    const request = route.request(), endpoint = new URL(request.url()).pathname.replace('/api/v1', '');
    let payload;
    if (request.method() === 'POST') {
      if (endpoint === '/work-orders') payload = session;
      else if (endpoint === '/work-orders/created-wo/submit') {
        submits++;
        if (submitFailure) { submitFailure = false; return route.fulfill({ status: 503, json: { error: { message: 'Pengajuan belum diterima. Coba lagi.' } } }); }
        session = { ...session, version: 2, state: 'queued' }; payload = session;
      } else if (endpoint === '/demo/sourcing-runs') payload = { ...baseRun, id: 'created-run', status: 'fulfilled_source', vendors: [] };
      else if (endpoint === '/work-orders/created-wo/answers') { session = { ...session, version: 4, state: 'processing', questions: [] }; payload = session; }
      else throw new Error(`Forbidden WO fixture write ${endpoint}`);
    } else if (endpoint === '/demo/config') payload = config;
    else if (endpoint === '/work-orders/created-wo' || endpoint === '/demo/orders/created-wo') payload = session;
    else if (endpoint === '/demo/orders') {
      if (orderReadFailure) { orderReadFailure = false; return route.fulfill({ status: 503, json: { error: { message: 'Daftar sementara tidak tersedia.' } } }); }
      payload = { generation: 1, items: [session] };
    } else if (endpoint === '/whatsapp/status') payload = { connection: 'disconnected', can_start: false, recipients: [] };
    else throw new Error(`Unexpected WO fixture API ${endpoint}`);
    await route.fulfill({ json: payload });
  });
  try {
    await page.goto(`${url}/technician/`);
    await page.getByRole('textbox', { name: /Apa masalahnya/ }).fill('Bearing conveyor diameter luar 30 mm');
    await page.getByRole('button', { name: 'Cari bearing', exact: true }).click();
    await page.getByText('Pengajuan belum diterima. Coba lagi.', { exact: true }).waitFor();
    assert.equal(await page.getByRole('dialog').count(), 0, 'A failed submit must not show success');
    await page.getByRole('link', { name: 'Buka draf dan periksa status' }).click();
    await page.getByRole('button', { name: 'Kirim draf untuk identifikasi' }).click();
    await page.getByRole('heading', { name: 'Work order berhasil diajukan' }).waitFor();
    assert.equal(submits, 2);
    await page.screenshot({ path: path.join(artifacts, 'wo-submit-success.png'), fullPage: true });
    assert.equal(await page.getByRole('dialog').getByRole('link', { name: 'Ke Meja manajer', exact: true }).count(), 0);
    await page.getByRole('button', { name: 'Lanjutkan klarifikasi', exact: true }).click();
    assert.match(page.url(), /technician\/clarification/);
    await page.getByText(/Identifikasi sedang berjalan/).waitFor();
    await page.getByRole('navigation', { name: 'Menu utama' }).getByRole('link', { name: 'Meja manajer', exact: true }).click();
    await page.getByRole('link', { name: 'Pantau identifikasi →', exact: true }).waitFor();
    assert.equal(await page.getByRole('link', { name: 'Buka stok & perbandingan →', exact: true }).count(), 0);
    orderReadFailure = true;
    await page.clock.runFor(5100);
    await page.getByText('Daftar sementara tidak tersedia.', { exact: true }).waitFor();
    session = { ...session, version: 3, state: 'awaiting_clarification', questions: [{ id: 'brand', key: 'brand', prompt: 'Merek apa yang terlihat?' }] };
    await page.clock.runFor(5100);
    await page.getByRole('link', { name: 'Jawab klarifikasi →', exact: true }).waitFor();
    session = { ...session, version: 5, state: 'identified', questions: [] };
    await page.clock.runFor(5100);
    await page.getByRole('link', { name: 'Buka stok & perbandingan →', exact: true }).waitFor();
    // Decision page also follows queued/clarification/identified without relying on list membership.
    session = { ...session, version: 3, state: 'awaiting_clarification' };
    await page.goto(`${url}/manager/decision/?session=created-wo`);
    await page.getByRole('link', { name: 'Selesaikan identifikasi terlebih dahulu' }).waitFor();
    session = { ...session, version: 5, state: 'identified', questions: [] };
    await page.clock.runFor(5100);
    await page.getByText('Stok gudang asal mencukupi. Vendor tidak dihubungi. Ini belum berarti mesin selesai diperbaiki.').waitFor();
    await page.goto(`${url}/manager/`);
    await page.getByRole('link', { name: 'Buka stok & perbandingan →', exact: true }).waitFor();
    // A newly created/queued WO also gets an explicit confirmation before navigation.
    session = { ...session, version: 1, state: 'draft' };
    await page.goto(`${url}/technician/`);
    await page.getByRole('textbox', { name: /Apa masalahnya/ }).fill('Bearing baru diameter luar 30 mm');
    await page.getByRole('button', { name: 'Cari bearing', exact: true }).click();
    await page.getByRole('heading', { name: 'Work order berhasil diajukan' }).waitFor();
    await page.getByRole('button', { name: 'Lanjutkan klarifikasi', exact: true }).click();
    await page.getByText(/Identifikasi sedang berjalan/).waitFor();
    session = { ...session, version: 1, state: 'draft' };
    await page.goto(`${url}/technician/`);
    await page.getByRole('textbox', { name: /Apa masalahnya/ }).fill('Simpan dulu kebutuhan bearing');
    const previousSubmits = submits;
    await page.getByRole('button', { name: 'Simpan draf', exact: true }).click();
    await page.getByRole('heading', { name: 'Draf work order berhasil disimpan' }).waitFor();
    assert.equal(submits, previousSubmits, 'Saving a draft must not submit it for identification');
    assert.deepEqual(errors, []);
    console.log('PASS: no false submit success, saved-draft recovery, WO success modal/routes, manager retry after error, queued → clarification → identified guidance, direct decision-page status polling.');
  } finally { await context.close(); }
}

module.exports = { testLiveWorkflow, testWoLifecycle };
