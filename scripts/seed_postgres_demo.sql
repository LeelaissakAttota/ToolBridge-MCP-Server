-- ToolBridge PostgreSQL demo data (fictional library: books + loans).
-- Idempotent: safe to run more than once. Run as the database owner or a superuser:
--   psql -U postgres -d toolbridge -f scripts/seed_postgres_demo.sql
-- Afterwards toolbridge_ro (if the role exists) gets SELECT-only access.

BEGIN;

CREATE TABLE IF NOT EXISTS books (
    book_id        integer PRIMARY KEY,
    title          text    NOT NULL,
    author         text    NOT NULL,
    genre          text,
    published_year integer,
    copies         integer
);

CREATE TABLE IF NOT EXISTS loans (
    loan_id     integer PRIMARY KEY,
    book_id     integer REFERENCES books(book_id),
    member_name text,
    loan_date   date,
    return_date date
);

INSERT INTO books (book_id, title, author, genre, published_year, copies) VALUES
    (1, 'The Silent River', 'K. Rao',   'Fiction',    2018, 3),
    (2, 'Data Stories',     'M. Iyer',  'Technology', 2021, 2),
    (3, 'Hills of Coorg',   'A. Menon', 'Travel',     2015, 1),
    (4, 'Learning Agents',  'S. Reddy', 'Technology', 2024, 4),
    (5, 'Kitchen Science',  'P. Nair',  'Cooking',    2019, 2),
    (6, 'Midnight Market',  'R. Das',   'Fiction',    2022, 3),
    (7, 'Budget Basics',    'L. Shah',  'Finance',    2020, 2),
    (8, 'Stars Over Hampi', 'V. Gowda', 'History',    2017, 1)
ON CONFLICT (book_id) DO UPDATE SET
    title = EXCLUDED.title, author = EXCLUDED.author, genre = EXCLUDED.genre,
    published_year = EXCLUDED.published_year, copies = EXCLUDED.copies;

INSERT INTO loans (loan_id, book_id, member_name, loan_date, return_date) VALUES
    (1,  1, 'Asha',   '2026-10-01', '2026-10-10'),
    (2,  2, 'Ravi',   '2026-10-03', NULL),
    (3,  4, 'Meena',  '2026-10-05', NULL),
    (4,  4, 'Kiran',  '2026-10-06', '2026-10-15'),
    (5,  6, 'Sita',   '2026-10-08', NULL),
    (6,  1, 'Arjun',  '2026-10-11', NULL),
    (7,  7, 'Divya',  '2026-10-12', '2026-10-19'),
    (8,  2, 'Vikram', '2026-10-14', NULL),
    (9,  8, 'Priya',  '2026-10-15', NULL),
    (10, 5, 'Naveen', '2026-10-16', NULL)
ON CONFLICT (loan_id) DO UPDATE SET
    book_id = EXCLUDED.book_id, member_name = EXCLUDED.member_name,
    loan_date = EXCLUDED.loan_date, return_date = EXCLUDED.return_date;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'toolbridge_ro') THEN
        EXECUTE format('GRANT CONNECT ON DATABASE %I TO toolbridge_ro', current_database());
        GRANT USAGE ON SCHEMA public TO toolbridge_ro;
        GRANT SELECT ON books, loans TO toolbridge_ro;
    ELSE
        RAISE NOTICE 'Role toolbridge_ro not found; skipping grants.';
    END IF;
END
$$;

COMMIT;
