CREATE TABLE sales (
  id INTEGER PRIMARY KEY,
  region TEXT NOT NULL,
  amount REAL NOT NULL
);

INSERT INTO sales (region, amount) VALUES
  ('华东', 120.5),
  ('华南', 80),
  ('华东', 200);
