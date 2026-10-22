/* eslint-disable @typescript-eslint/no-require-imports -- Standalone CommonJS browser tests. */
const assert = require('node:assert/strict');

async function testAutoWhatsApp(browser, url, { config, baseSession, baseRun }) {
  const context = await browser.newContext();
  const page = await context.newPage();
  page.setDefaultTimeout(10000);
  await page.clock.install();
  let run = null, stockCreates = 0, starts = 0, connected = false, failStart = false;
  const recipients = [{ id: 'WA-A', label: 'Vendor A' }, { id: 'WA-B', label: 'Vendor B' }];
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/api/v1/**', async route => {
    const request = route.request(), endpoint = new URL(request.url()).pathname.replace('/api/v1', '');
    let payload;
    if (request.method() === 'POST') {
      if (endpoint === '/demo/sourcing-runs') {
        stockCreates++;
        run = { ...baseRun, vendors: Array.from({ length: 5 }, (_, i) => ({ vendor_id: `SIM-${i}`, outcome: 'pending', quote: null, initial_quote: null, counteroffers_used: 0, eligible: false })), exchanges: [], negotiation: null }; payload = run;
      } else if (endpoint === '/whatsapp/runs/run/start') {
        starts++;
        if (failStart) { failStart = false; return route.fulfill({ status: 503, json: { error: { message: 'Pengiriman tertunda.' } } }); }
        run = { ...run, transport: 'whatsapp', version: 2, vendors: recipients.map(recipient => ({ vendor_id: recipient.id, outcome: 'waiting', quote: null, initial_quote: null, counteroffers_used: 0, eligible: false })) }; payload = { conversations: [] };
      } else if (endpoint === '/demo/sourcing-runs/run/prepare-comparison') payload = { id: 'auto-comp', version: 1, source_run_version: 2, eligible_complete_options: [], unrankable_options: [], unexpired_option_ids: [], coverage_complete: false };
      else throw new Error(`Unexpected automatic write: ${endpoint}`);
    } else if (endpoint === '/demo/config') payload = config;
    else if (endpoint === '/demo/orders/session') payload = { ...baseSession, run_id: run?.id, comparison_id: null };
    else if (endpoint === '/demo/sourcing-runs/run') payload = run;
    else if (endpoint === '/whatsapp/status') payload = { connection: connected ? 'connected' : 'disconnected', can_start: true, recipients };
    else if (endpoint === '/whatsapp/conversations') payload = { conversations: [] };
    else if (endpoint === '/demo/comparisons/auto-comp') payload = { id: 'auto-comp', version: 1, source_run_version: 2, eligible_complete_options: [], unrankable_options: [], unexpired_option_ids: [], coverage_complete: false };
    else throw new Error(`Unexpected automatic read: ${endpoint}`);
    await route.fulfill({ json: payload });
  });
  try {
    await page.goto(`${url}/manager/decision/?session=session`);
    await page.getByRole('button', { name: 'Coba hubungkan penawaran lagi' }).waitFor();
    assert.equal(stockCreates, 1);
    assert.equal(starts, 0, 'Disconnected bridge must not receive start writes');
    assert.equal(await page.getByRole('navigation', { name: 'Menu utama' }).getByRole('link', { name: 'WhatsApp', exact: true }).count(), 0);
    assert.equal(await page.getByText('Pilih cara mencari penawaran vendor', { exact: true }).count(), 0);
    assert.equal(await page.getByRole('button', { name: 'Jalankan simulator & bandingkan' }).count(), 0);
    connected = true; failStart = true;
    await page.getByRole('button', { name: 'Coba hubungkan penawaran lagi' }).click();
    await page.getByText('Pengiriman tertunda.', { exact: true }).waitFor();
    await page.clock.runFor(15100);
    assert.equal(starts, 1, 'Failed start must not retry in a polling loop');
    await page.getByRole('button', { name: 'Coba hubungkan penawaran lagi' }).click();
    await page.getByRole('heading', { name: 'Percakapan vendor' }).waitFor();
    assert.equal(starts, 2);
    await page.clock.runFor(15100);
    assert.equal(starts, 2, 'WA polling must not duplicate RFQs');
    await page.reload();
    await page.getByRole('heading', { name: 'Percakapan vendor' }).waitFor();
    await page.clock.runFor(5100);
    assert.equal(starts, 2, 'Reloaded existing WA run must not start again');
    assert.equal(stockCreates, 1, 'Reload must reuse the persisted run');
    // Fresh connected flow requires no transport selection or extra click.
    run = null;
    await page.reload();
    await page.getByRole('heading', { name: 'Percakapan vendor' }).waitFor();
    assert.equal(stockCreates, 2);
    assert.equal(starts, 3);
    run = { ...run, vendors: run.vendors.slice(0, 1) };
    await page.reload();
    await page.getByRole('button', { name: 'Coba lengkapi pengiriman penawaran' }).waitFor();
    assert.equal(starts, 3, 'A partial legacy start must expose recovery without automatic resends');
    await page.getByRole('button', { name: 'Coba lengkapi pengiriman penawaran' }).click();
    await page.getByRole('heading', { name: 'Percakapan vendor' }).waitFor();
    await page.clock.runFor(100);
    assert.equal(starts, 4);
    assert.equal(await page.getByRole('button', { name: 'Coba lengkapi pengiriman penawaran' }).count(), 0);
    assert.deepEqual(errors, []);
    console.log('PASS: automatic stock/WhatsApp flow, no transport selector or WA tab, disconnected status, explicit retry without floods, persisted run/reload idempotence. All APIs mocked.');
  } finally { await context.close(); }
}
module.exports = { testAutoWhatsApp };
