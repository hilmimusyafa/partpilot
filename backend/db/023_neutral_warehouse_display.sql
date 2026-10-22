-- Shared synthetic warehouse labels apply to both legacy AC and food demos.
-- This changes display metadata only, never stock, identity or source evidence.
UPDATE pp.demo_warehouse_display
SET name='Gudang 1 - Produksi Cikarang',
    address='Jl. Contoh Produksi No. 1, Cikarang Utara, Bekasi - ALAMAT DUMMY'
WHERE warehouse_id='SYN-WH-01' AND simulated;
