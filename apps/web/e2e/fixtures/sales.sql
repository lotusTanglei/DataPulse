CREATE TABLE sales (
  id INTEGER PRIMARY KEY,
  month TEXT NOT NULL,
  region TEXT NOT NULL,
  amount REAL NOT NULL,
  target REAL NOT NULL,
  area_code TEXT NOT NULL
);

INSERT INTO sales (month, region, amount, target, area_code) VALUES
  ('2026-01', '华东', 120.5, 150, 'east'),
  ('2026-02', '华南', 80, 100, 'south'),
  ('2026-03', '华东', 200, 180, 'east'),
  ('2026-04', '华北', 160, 140, 'north');
