// Runs only against a local static build and intercepted synthetic API responses.
// Supply Playwright through NODE_PATH if it is not installed in the repository.
/* eslint-disable @typescript-eslint/no-require-imports -- Standalone CommonJS test supports an external Playwright runtime through NODE_PATH. */
const { chromium } = require('playwright');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '../out');
const artifacts = path.resolve(__dirname, '../.next/ui-smoke');
fs.mkdirSync(artifacts, { recursive: true });
const server = http.createServer((req, res) => {
  const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
  let file = path.resolve(root, '.' + pathname);
  if (!file.startsWith(root + path.sep) && file !== root) { res.writeHead(403).end(); return; }
  if (fs.existsSync(file) && fs.statSync(file).isDirectory()) file = path.join(file, 'index.html');
  if (!fs.existsSync(file)) { res.writeHead(404).end(); return; }
  const mime = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml' };
  res.setHeader('Content-Type', mime[path.extname(file)] || 'text/plain');
  fs.createReadStream(file).pipe(res);
});

const config = { generation: 1, context: {}, assumptions: {}, warehouses: Array.from({ length: 5 }, (_, index) => ({ id: `SYN-WH-0${index + 1}`, name: `Gudang ${index + 1}`, address: `Jl. Contoh ${index + 1}, Kota Demo`, simulated: true })), scenarios: [{ id: 'main', label: 'Bearing fisik 30 mm', description: 'Bearing conveyor berisik. Diameter luar 30 mm.', quantity: '6', warehouse_id: 'SYN-WH-01' }] };
const quote = { unit_price: '10000', qty_available: '8', shipping_amount: '1000', tax_amount: '6000', delivered_eta: '2099-01-01T08:00:00Z', valid_until: '2099-01-02T08:00:00Z', processing_hours: '1' };
const option = (id, kind, total) => ({ option_id: id, source_id: id, source_kind: kind, item_code: kind === 'warehouse' ? 'G2-BRG-017' : undefined, quote, valid_until: quote.valid_until, economics: { sourcing_total: '67000', unrecoverable_lost_contribution: String(total - 67000), incremental_disruption_total: '0', future_relevant_option_total: String(total) } });
// Deliberately interleaved and unsorted so rank assertions exercise presentation order.
const comparison = { id: 'comparison', version: 1, source_run_version: 1, eligible_complete_options: [option('vendor-expensive', 'vendor', 300000), option('warehouse-best', 'warehouse', 100000), option('vendor-best', 'vendor', 200000)], unrankable_options: [ { option_id: 'warehouse-low', source_id: 'SYN-WH-01', source_kind: 'warehouse', reasons: ['insufficient_stock'] }, { option_id: 'vendor-missing', source_id: 'Vendor belum lengkap', source_kind: 'vendor', reasons: ['no_valid_quote'] } ], unexpired_option_ids: ['vendor-expensive', 'warehouse-best', 'vendor-best'], coverage_complete: false };
const baseSession = { id: 'session', version: 1, state: 'identified', description: 'Bearing conveyor diameter luar 30 mm', quantity: '6', warehouse_id: 'SYN-WH-01', urgency: 'High', run_id: 'run', comparison_id: 'comparison', facts: [], questions: [] };
comparison.eligible_complete_options.push({ ...option('vendor-expired', 'vendor', 400000), valid_until: '2020-01-01T00:00:00Z' });
const scope = { warehouse_id: 'SYN-WH-01', status: 'insufficient', item_code: 'NTN-6200LLU', available_qty: '4', actual_qty: '4', reserved_qty: '0' };
const baseRun = { id: 'run', version: 1, status: 'sourcing', quantity: '6', transport: 'simulator', identity: { brand: 'NTN', base: '6200', suffix: 'LLU' }, availability: { origin: scope, alternatives: [{ ...scope, warehouse_id: 'SYN-WH-02', item_code: 'G2-BRG-017', available_qty: '8', actual_qty: '8', status: 'sufficient' }], complete: true }, vendors: [{ vendor_id: 'vendor-best', outcome: 'quoted', counteroffers_used: 0, quote, initial_quote: quote, eligible: true }], negotiation: { policy: 'best-total-minus-10pct-v1', round: 1, best_option_id: 'warehouse-best', best_total: '100000', target_total: '90000', basis_at: '2099-01-01', vendors: [{ vendor_id: 'vendor-best', status: 'skipped', reason: 'already_below_target', target_unit_price: null }] } };

baseRun.vendors.push({ vendor_id: 'SIM-SHORT', outcome: 'quoted', counteroffers_used: 0, quote: { ...quote, qty_available: '2' }, initial_quote: quote, eligible: false });
baseRun.vendors.push({ vendor_id: 'SIM-NO-RESPONSE', outcome: 'no_response', counteroffers_used: 0, quote: null, initial_quote: null, eligible: false });

async function main() {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const url = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome', headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    let decision = null;
    let poReads = 0;
    let failNextPoRead = false;
    const writes = [];
    await page.route('**/api/v1/**', async route => {
      const request = route.request();
      const endpoint = new URL(request.url()).pathname.replace('/api/v1', '');
      if (request.method() === 'POST') {
        writes.push(endpoint);
        assert.equal(endpoint, '/demo/comparisons/comparison/decision', 'Only an explicitly clicked local fixture decision may be written');
        decision = request.postDataJSON().option_id;
        return route.fulfill({ json: { option_id: decision } });
      }
      let payload;
      if (endpoint === '/demo/config') payload = config;
      else if (endpoint === '/demo/orders') payload = { generation: 1, items: [{ ...baseSession, decision: decision && { option_id: decision } }] };
      else if (endpoint === '/demo/orders/session') payload = { ...baseSession, decision: decision && { option_id: decision } };
      else if (endpoint === '/demo/sourcing-runs/run') payload = { ...baseRun, decision: decision && { option_id: decision } };
      else if (endpoint === '/demo/comparisons/comparison') payload = comparison;
      else if (endpoint === '/whatsapp/status') payload = { connection: 'disconnected', qr_data_url: null, can_start: false, recipients: [] };
      else if (endpoint === '/demo/sourcing-runs/run/purchase-order') {
        poReads++;
        if (failNextPoRead) { failNextPoRead = false; return route.fulfill({ status: 503, json: { error: { message: 'Dokumen sementara tidak dapat dimuat.' } } }); }
        payload = { purchase_order: decision?.startsWith('vendor') ? { id: 'po-1', number: 'PP-DEMO-001', supplier: { id: 'vendor-best', name: 'Vendor terbaik' }, quantity: '6', unit_price: '10000', total: '67000' } : null };
      }
      else if (endpoint === '/work-orders/clarification') payload = { ...baseSession, id: 'clarification', state: 'awaiting_clarification', questions: [{ id: 'brand', prompt: 'Merek apa yang terlihat?' }, { id: 'size', prompt: 'Berapa diameter dalam dan lebarnya?' }, { id: 'seal', prompt: 'Penutup bearing karet atau logam?' }] };
      else throw new Error(`Unexpected local API request ${endpoint}`);
      await route.fulfill({ json: payload });
    });
    await page.goto(`${url}/technician/`);
    await page.getByRole('button', { name: 'Cari bearing', exact: true }).waitFor();
    assert.equal(await page.getByRole('spinbutton', { name: /Jumlah/ }).inputValue(), '6');
    await page.getByRole('button', { name: 'Tambah jumlah' }).click();
    assert.equal(await page.getByRole('spinbutton', { name: /Jumlah/ }).inputValue(), '7');
    await page.getByRole('button', { name: 'Kurangi jumlah' }).click();
    await page.screenshot({ path: path.join(artifacts, 'technician-desktop.png'), fullPage: true });
    await page.goto(`${url}/technician/clarification/?session=clarification`);
    await page.getByRole('textbox', { name: 'Merek apa yang terlihat?' }).waitFor();
    assert.equal(await page.getByRole('textbox').count(), 3);
    await page.screenshot({ path: path.join(artifacts, 'clarification-desktop.png'), fullPage: true });
    await page.goto(`${url}/manager/decision/?session=session`);
    const warehouses = page.getByRole('region', { name: 'Sumber gudang', exact: true });
    const vendors = page.getByRole('region', { name: 'Penawaran vendor', exact: true });
    await vendors.getByRole('button', { name: 'Setujui PO' }).first().waitFor();
    await page.getByRole('heading', { name: 'Rekomendasi berdasarkan biaya', exact: true }).waitFor();
    assert.match(await warehouses.innerText(), /#1 global/);
    const stock = page.getByRole('region', { name: 'Stok barang yang sama di setiap gudang' });
    assert.equal(await stock.getByRole('article').count(), 5);
    assert.match(await stock.getByRole('article', { name: 'Gudang 1', exact: true }).innerText(), /Kekurangan[\s\S]*2/);
    assert.match(await stock.innerText(), /Jl. Contoh 5/);
    const vendorText = await vendors.innerText();
    assert(vendorText.indexOf('vendor-best') < vendorText.indexOf('vendor-expensive'));
    assert.match(vendorText, /#2 global[\s\S]*#3 global/);
    assert.match(await page.locator('body').innerText(), /Dilewati/);
    await page.getByText('Stok tidak mencukupi — tidak ditawar', { exact: true }).waitFor();
    await page.getByText('Menunggu balasan vendor — belum ditawar', { exact: true }).waitFor();
    await page.getByRole('columnheader', { name: 'Tawaran harga', exact: true }).waitFor();
    assert.equal(await vendors.getByRole('button', { name: 'Kedaluwarsa', exact: true }).isDisabled(), true);
    assert.equal(await page.getByText('Menunggu jawaban negosiasi', { exact: true }).count(), 0);
    await page.screenshot({ path: path.join(artifacts, 'decision-desktop.png'), fullPage: true });
    await vendors.getByRole('button', { name: 'Setujui PO' }).first().click();
    failNextPoRead = true;
    await page.getByRole('button', { name: 'Konfirmasi PO demo', exact: true }).click();
    await page.getByText('Dokumen sementara tidak dapat dimuat.', { exact: true }).waitFor();
    assert.equal(writes.length, 1, 'PO retrieval failure must not repeat the approved decision');
    await page.getByRole('button', { name: 'Muat ulang PO', exact: true }).click();
    await page.getByRole('link', { name: 'Unduh PO (PDF)' }).waitFor();
    assert.equal(await page.getByRole('link', { name: 'Unduh PO (PDF)' }).getAttribute('href'), '/api/v1/demo/purchase-orders/po-1/pdf');
    assert.equal(decision, 'vendor-best');
    assert.match(await page.getByRole('region', { name: 'Purchase Order demo' }).innerText(), /67[.]000/);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(artifacts, 'purchase-order-desktop.png'), fullPage: true });
    await page.reload();
    await page.getByRole('link', { name: 'Unduh PO (PDF)' }).waitFor();
    assert(poReads >= 2, 'PO must be retrieved again after page reload');
    decision = null;
    await page.reload();
    await warehouses.getByRole('button', { name: 'Pilih gudang' }).click();
    const previousPoReads = poReads;
    await page.getByRole('button', { name: 'Konfirmasi pilihan gudang' }).click();
    await page.getByRole('heading', { name: 'Request mutasi berhasil dicatat' }).waitFor();
    assert.equal(decision, 'warehouse-best');
    assert.equal(poReads, previousPoReads, 'Warehouse choice must not fetch a PO');
    await page.getByRole('button', { name: 'Selesai', exact: true }).click();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(artifacts, 'decision-mobile.png'), fullPage: true });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'Mobile page must not overflow horizontally');
    await page.goto(`${url}/manager/`);
    await page.getByRole('heading', { name: 'Order list', exact: true }).waitFor();
    await page.getByRole('link', { name: 'Buka stok & perbandingan →' }).waitFor();
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.screenshot({ path: path.join(artifacts, 'manager-desktop.png'), fullPage: true });
    await page.getByRole('textbox', { name: 'Cari work order' }).fill('not present');
    await page.getByText('Tidak ada WO yang sesuai pencarian atau filter.').waitFor();
    assert.deepEqual(errors, []);
    assert.equal(writes.length, 2);
    console.log('PASS: form controls, clarification, global sorted ranks, skipped negotiation, expired quote disabled, vendor approval/PO/retry/reload, warehouse popup, mobile overflow, manager search, no browser errors. All APIs mocked locally.');
    console.log(`Screenshots: ${artifacts}`);
    await context.close();
    const { testLiveWorkflow, testWoLifecycle } = require('./live-workflow.cjs');
    await testLiveWorkflow(browser, url, { config, baseSession, baseRun, quote, option }, artifacts);
    await testWoLifecycle(browser, url, { config, baseSession }, artifacts);
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error); process.exitCode = 1; }).finally(() => server.close());
