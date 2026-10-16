-- TABLE CREATION

DROP TABLE IF EXISTS breweries;
DROP TABLE IF EXISTS cities;
DROP TABLE IF EXISTS countries;
DROP TABLE IF EXISTS brewery_types;

CREATE TABLE brewery_types (
    type_id INTEGER PRIMARY KEY,
    type_name TEXT NOT NULL UNIQUE
);

CREATE TABLE countries (
    country_id INTEGER PRIMARY KEY,
    country_name TEXT NOT NULL UNIQUE
);

CREATE TABLE cities (
    city_id INTEGER PRIMARY KEY,
    city_name TEXT NOT NULL,
    state TEXT,
    country_id INTEGER NOT NULL,
    UNIQUE (city_name, state, country_id),
    FOREIGN KEY (country_id) REFERENCES countries(country_id)
);

CREATE TABLE breweries (
    brewery_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type_id INTEGER NOT NULL,
    city_id INTEGER NOT NULL,
    address TEXT,
    postal_code TEXT,
    latitude REAL CHECK (latitude BETWEEN -90 AND 90),
    longitude REAL CHECK (longitude BETWEEN -180 AND 180),
    phone TEXT,
    website_url TEXT,
    has_website INTEGER CHECK (has_website IN (0, 1)),
    has_phone INTEGER CHECK (has_phone IN (0, 1)),
    has_coordinates INTEGER CHECK (has_coordinates IN (0, 1)),
    FOREIGN KEY (type_id) REFERENCES brewery_types(type_id),
    FOREIGN KEY (city_id) REFERENCES cities(city_id)
);

-- REPORTING QUERIES

-- 1. Breweries per type (JOIN + GROUP BY)
SELECT t.type_name, COUNT(*) AS total_breweries
        FROM breweries b
        JOIN brewery_types t ON b.type_id = t.type_id
        GROUP BY t.type_name
        ORDER BY total_breweries DESC;

-- 2. Top 10 countries (JOIN)
SELECT co.country_name, COUNT(*) AS total_breweries
        FROM breweries b
        JOIN cities c ON b.city_id = c.city_id
        JOIN countries co ON c.country_id = co.country_id
        GROUP BY co.country_name
        ORDER BY total_breweries DESC
        LIMIT 10;

-- 3. Top 10 cities
SELECT c.city_name, c.state, COUNT(*) AS total_breweries
        FROM breweries b
        JOIN cities c ON b.city_id = c.city_id
        WHERE c.city_name != 'Unknown'
        GROUP BY c.city_id
        ORDER BY total_breweries DESC
        LIMIT 10;

-- 4. States with more than 100 breweries (HAVING)
SELECT c.state, co.country_name, COUNT(*) AS total_breweries
        FROM breweries b
        JOIN cities c ON b.city_id = c.city_id
        JOIN countries co ON c.country_id = co.country_id
        GROUP BY c.state, co.country_name
        HAVING COUNT(*) > 100
        ORDER BY total_breweries DESC;

-- 5. Website availability (CASE)
SELECT
            CASE
                WHEN has_website = 1 THEN 'Has website'
                ELSE 'No website'
            END AS website_status,
            COUNT(*) AS total_breweries
        FROM breweries
        GROUP BY website_status;

-- 6. Types with above-average brewery count (subquery)
SELECT t.type_name, COUNT(*) AS total_breweries
        FROM breweries b
        JOIN brewery_types t ON b.type_id = t.type_id
        GROUP BY t.type_name
        HAVING COUNT(*) > (
            SELECT COUNT(*) * 1.0 / (SELECT COUNT(*) FROM brewery_types)
            FROM breweries
        )
        ORDER BY total_breweries DESC;

-- 7. Coordinate coverage by country, countries with 50+ breweries
SELECT co.country_name,
               COUNT(*) AS total_breweries,
               ROUND(100.0 * SUM(b.has_coordinates) / COUNT(*), 1) AS pct_with_coordinates
        FROM breweries b
        JOIN cities c ON b.city_id = c.city_id
        JOIN countries co ON c.country_id = co.country_id
        GROUP BY co.country_name
        HAVING COUNT(*) >= 50
        ORDER BY pct_with_coordinates DESC;

-- 8. Top 10 cities for brewpubs
SELECT c.city_name, c.state, COUNT(*) AS brewpubs
        FROM breweries b
        JOIN brewery_types t ON b.type_id = t.type_id
        JOIN cities c ON b.city_id = c.city_id
        WHERE t.type_name = 'brewpub' AND c.city_name != 'Unknown'
        GROUP BY c.city_id
        ORDER BY brewpubs DESC
        LIMIT 10;

