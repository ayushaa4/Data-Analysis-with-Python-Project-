import os
import json
import sqlite3
import requests
import pandas as pd
import matplotlib.pyplot as plt

os.makedirs("data", exist_ok=True)

# EXTRACT DATA
# Source 1: breweries.csv (from the Open Brewery DB repo)
# phone and postal_code are read as text so numbers don't lose leading zeros
df = pd.read_csv("breweries.csv", dtype={"phone": str, "postal_code": str})

# Keep an untouched copy of the raw data
df.to_csv("data/breweries_raw.csv", index=False)
print("Raw rows:", df.shape[0], "Raw columns:", df.shape[1])

# Source 2: Open Brewery DB API (200 records, saved as raw JSON)
try:
    response = requests.get("https://api.openbrewerydb.org/v1/breweries",
                            params={"per_page": 200}, timeout=30)
    response.raise_for_status()
    api_data = response.json()
    with open("data/api_raw.json", "w", encoding="utf-8") as f:
        json.dump(api_data, f)
    api_df = pd.DataFrame(api_data)
    found = api_df["id"].isin(df["id"]).sum()
    print("API records:", len(api_df), "| also found in CSV:", found)
except requests.RequestException as error:
    print("API request failed:", error)

# EXPLORE DATA (EDA)
print("\nShape:", df.shape)
print("\nColumn names:")
print(df.columns.tolist())
print("\nFirst 5 rows:")
print(df.head())
df.info()

print("\nSummary statistics:")
print(df.describe(include="all"))

print("\nMissing values:")
print(df.isnull().sum())

print("\nDuplicate rows:", df.duplicated().sum())
print("Duplicate ids:", df["id"].duplicated().sum())

print("\nUnique values per column:")
print(df.nunique())

print("\nBrewery types:")
print(df["brewery_type"].value_counts(dropna=False))

print("\nTop 10 countries:")
print(df["country"].value_counts(dropna=False).head(10))

print("\nCoordinate data types:", df["latitude"].dtype, df["longitude"].dtype)
lat = pd.to_numeric(df["latitude"], errors="coerce")
lon = pd.to_numeric(df["longitude"], errors="coerce")
print("Invalid latitudes (outside -90 to 90):", ((lat < -90) | (lat > 90)).sum())
print("Invalid longitudes (outside -180 to 180):", ((lon < -180) | (lon > 180)).sum())

print("\nNames with extra spaces:", df["name"].ne(df["name"].str.strip()).sum())
print("Empty text in city:", (df["city"] == "").sum())

# Exploratory analysis (before cleaning)
print("\nBreweries per country (top 5):")
eda_country = df.groupby("country").agg(total_breweries=("id", "count"))
print(eda_country.sort_values("total_breweries", ascending=False).head(5))

print("\nFirst 3 rows, first 4 columns (iloc):")
print(df.iloc[:3, :4])

print("\nSample brewpub names (loc):")
print(df.loc[df["brewery_type"] == "brewpub", "name"].head())

# Filtering: US breweries with no website
us_no_site = df[(df["country"] == "United States") & (df["website_url"].isnull())]
print("\nUS breweries without a website:", len(us_no_site))

# Calculated column: how many fields are missing in each row
missing_per_row = df.isnull().sum(axis=1)
print("\nMissing fields per brewery:")
print(missing_per_row.value_counts().sort_index())

missing_per_row.value_counts().sort_index().plot(kind="bar", figsize=(7, 4))
plt.title("Number of Missing Fields per Brewery")
plt.xlabel("Missing fields")
plt.ylabel("Number of Breweries")
plt.tight_layout()
plt.savefig("data/chart_missing_fields.png")
plt.close()

# CLEAN DATA
wanted = ["id", "name", "brewery_type", "address_1", "city", "state_province",
          "postal_code", "country", "latitude", "longitude", "phone", "website_url"]
columns_needed = [c for c in wanted if c in df.columns]
brew = df[columns_needed].copy()

# Remove duplicate breweries
brew = brew.drop_duplicates(subset="id")

# Trim spaces and turn empty text into missing values
text_columns = ["id", "name", "brewery_type", "address_1", "city", "state_province",
                "postal_code", "country", "phone", "website_url"]
for column in text_columns:
    if column in brew.columns:
        brew[column] = brew[column].str.strip()
        brew[column] = brew[column].replace("", float("nan"))

# Correct data types: coordinates must be numbers
brew["latitude"] = pd.to_numeric(brew["latitude"], errors="coerce")
brew["longitude"] = pd.to_numeric(brew["longitude"], errors="coerce")

# Invalid coordinates become missing
brew.loc[(brew["latitude"] < -90) | (brew["latitude"] > 90), "latitude"] = float("nan")
brew.loc[(brew["longitude"] < -180) | (brew["longitude"] > 180), "longitude"] = float("nan")

# Standardize text
brew["brewery_type"] = brew["brewery_type"].str.lower()

# Fill missing categories so every brewery can be linked to a table
brew["brewery_type"] = brew["brewery_type"].fillna("unknown")
brew["city"] = brew["city"].fillna("Unknown")
brew["state_province"] = brew["state_province"].fillna("Unknown")
brew["country"] = brew["country"].fillna("Unknown")

# Rename columns
brew = brew.rename(columns={"id": "brewery_id",
                            "address_1": "address",
                            "state_province": "state"})

print("\nRows after cleaning:", len(brew))
print(brew.isnull().sum())

# TRANSFORM DATA
# Calculated columns (1 = yes, 0 = no)
brew["has_website"] = brew["website_url"].notna().astype(int)
brew["has_phone"] = brew["phone"].notna().astype(int)
brew["has_coordinates"] = (brew["latitude"].notna() & brew["longitude"].notna()).astype(int)

# Split the flat data into related tables

# brewery_types table
brewery_types = brew[["brewery_type"]].drop_duplicates().reset_index(drop=True)
brewery_types["type_id"] = brewery_types.index + 1
brewery_types = brewery_types.rename(columns={"brewery_type": "type_name"})
brewery_types = brewery_types[["type_id", "type_name"]]

# countries table
countries = brew[["country"]].drop_duplicates().reset_index(drop=True)
countries["country_id"] = countries.index + 1
countries = countries.rename(columns={"country": "country_name"})
countries = countries[["country_id", "country_name"]]

# cities table (each city belongs to one country)
city_keys = brew[["city", "state", "country"]].drop_duplicates().reset_index(drop=True)
city_keys["city_id"] = city_keys.index + 1
cities = city_keys.merge(countries, left_on="country", right_on="country_name")
cities = cities[["city_id", "city", "state", "country_id"]]
cities = cities.rename(columns={"city": "city_name"})

# breweries table (points to type and city)
breweries = brew.merge(brewery_types, left_on="brewery_type", right_on="type_name")
breweries = breweries.merge(city_keys, on=["city", "state", "country"])
breweries = breweries[["brewery_id", "name", "type_id", "city_id", "address",
                       "postal_code", "latitude", "longitude", "phone", "website_url",
                       "has_website", "has_phone", "has_coordinates"]]

print("\nbreweries:", breweries.shape)
print("brewery_types:", brewery_types.shape)
print("countries:", countries.shape)
print("cities:", cities.shape)

# ANALYSIS AND INSIGHTS
# One combined table, only used for analysis
full = breweries.merge(brewery_types, on="type_id")
full = full.merge(cities, on="city_id")
full = full.merge(countries, on="country_id")

# Q1. Which brewery types are most common?
print("\nQ1. Breweries by Type")
q1 = full["type_name"].value_counts()
print(q1)

# Q2. Which countries have the most breweries?
print("\nQ2. Top 10 Countries")
q2 = full["country_name"].value_counts().head(10)
print(q2)

# Q3. Which cities have the most breweries?
print("\nQ3. Top 10 Cities")
known_cities = full[full["city_name"] != "Unknown"]
q3 = known_cities.groupby(["city_name", "state"]).size()
q3 = q3.sort_values(ascending=False).head(10)
print(q3)

# Q4. What brewery types are common in the top 5 countries?
print("\nQ4. Brewery Types in the Top 5 Countries")
top5 = q2.head(5).index
q4 = pd.crosstab(full[full["country_name"].isin(top5)]["country_name"],
                 full[full["country_name"].isin(top5)]["type_name"])
print(q4)

# Q5. Which brewery types are most likely to have a website?
print("\nQ5. Share of Breweries with a Website, by Type (%)")
q5 = (full.groupby("type_name")["has_website"].mean() * 100).round(1)
q5 = q5.sort_values(ascending=False)
print(q5)

# Q6. How complete is the location data in the top 10 countries?
print("\nQ6. Share of Breweries with Coordinates, by Country (%)")
top10 = q2.index
q6 = full[full["country_name"].isin(top10)]
q6 = (q6.groupby("country_name")["has_coordinates"].mean() * 100).round(1)
q6 = q6.sort_values(ascending=False)
print(q6)

# Charts (saved as images, so the script doesn't stop)
q1.plot(kind="bar", figsize=(9, 5))
plt.title("Number of Breweries by Type")
plt.xlabel("Brewery Type")
plt.ylabel("Number of Breweries")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("data/chart_types.png")
plt.close()

q2.plot(kind="bar", figsize=(10, 5))
plt.title("Top 10 Countries by Brewery Count")
plt.xlabel("Country")
plt.ylabel("Number of Breweries")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("data/chart_countries.png")
plt.close()

# INSIGHTS (write these after running, using your real numbers)
# Insight 1:
# Insight 2:
# Insight 3:
# Insight 4:
# Insight 5:

# DATABASE DESIGN
conn = sqlite3.connect("data/breweries.db")
cursor = conn.cursor()

# Make SQLite enforce foreign keys
cursor.execute("PRAGMA foreign_keys = ON")

# Table definitions (also saved in the .sql file at the end)
schema_sql = """
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
"""

# Drops old tables and creates fresh ones, so the script can be re-run
cursor.executescript(schema_sql)
conn.commit()

# LOAD DATA INTO DATABASE
# Parent tables first, then the tables that point to them
brewery_types.to_sql("brewery_types", conn, if_exists="append", index=False)
countries.to_sql("countries", conn, if_exists="append", index=False)
cities.to_sql("cities", conn, if_exists="append", index=False)
breweries.to_sql("breweries", conn, if_exists="append", index=False)

print("\nRows loaded:")
for table_name in ["brewery_types", "countries", "cities", "breweries"]:
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    print(table_name, cursor.fetchone()[0])

# SQL REPORTING (8 queries)
queries = {

    "1. Breweries per type (JOIN + GROUP BY)": """
        SELECT t.type_name, COUNT(*) AS total_breweries
        FROM breweries b
        JOIN brewery_types t ON b.type_id = t.type_id
        GROUP BY t.type_name
        ORDER BY total_breweries DESC
    """,

    "2. Top 10 countries (JOIN)": """
        SELECT co.country_name, COUNT(*) AS total_breweries
        FROM breweries b
        JOIN cities c ON b.city_id = c.city_id
        JOIN countries co ON c.country_id = co.country_id
        GROUP BY co.country_name
        ORDER BY total_breweries DESC
        LIMIT 10
    """,

    "3. Top 10 cities": """
        SELECT c.city_name, c.state, COUNT(*) AS total_breweries
        FROM breweries b
        JOIN cities c ON b.city_id = c.city_id
        WHERE c.city_name != 'Unknown'
        GROUP BY c.city_id
        ORDER BY total_breweries DESC
        LIMIT 10
    """,

    "4. States with more than 100 breweries (HAVING)": """
        SELECT c.state, co.country_name, COUNT(*) AS total_breweries
        FROM breweries b
        JOIN cities c ON b.city_id = c.city_id
        JOIN countries co ON c.country_id = co.country_id
        GROUP BY c.state, co.country_name
        HAVING COUNT(*) > 100
        ORDER BY total_breweries DESC
    """,

    "5. Website availability (CASE)": """
        SELECT
            CASE
                WHEN has_website = 1 THEN 'Has website'
                ELSE 'No website'
            END AS website_status,
            COUNT(*) AS total_breweries
        FROM breweries
        GROUP BY website_status
    """,

    "6. Types with above-average brewery count (subquery)": """
        SELECT t.type_name, COUNT(*) AS total_breweries
        FROM breweries b
        JOIN brewery_types t ON b.type_id = t.type_id
        GROUP BY t.type_name
        HAVING COUNT(*) > (
            SELECT COUNT(*) * 1.0 / (SELECT COUNT(*) FROM brewery_types)
            FROM breweries
        )
        ORDER BY total_breweries DESC
    """,

    "7. Coordinate coverage by country, countries with 50+ breweries": """
        SELECT co.country_name,
               COUNT(*) AS total_breweries,
               ROUND(100.0 * SUM(b.has_coordinates) / COUNT(*), 1) AS pct_with_coordinates
        FROM breweries b
        JOIN cities c ON b.city_id = c.city_id
        JOIN countries co ON c.country_id = co.country_id
        GROUP BY co.country_name
        HAVING COUNT(*) >= 50
        ORDER BY pct_with_coordinates DESC
    """,

    "8. Top 10 cities for brewpubs": """
        SELECT c.city_name, c.state, COUNT(*) AS brewpubs
        FROM breweries b
        JOIN brewery_types t ON b.type_id = t.type_id
        JOIN cities c ON b.city_id = c.city_id
        WHERE t.type_name = 'brewpub' AND c.city_name != 'Unknown'
        GROUP BY c.city_id
        ORDER BY brewpubs DESC
        LIMIT 10
    """,
}

os.makedirs("data/sql_results", exist_ok=True)

# The .sql file = table creation + the 8 reporting queries
sql_file = open("data/breweries_database.sql", "w", encoding="utf-8")
sql_file.write("-- TABLE CREATION\n" + schema_sql + "\n-- REPORTING QUERIES\n\n")

for number, (title, sql) in enumerate(queries.items(), 1):
    result = pd.read_sql_query(sql, conn)
    print("\n" + title)
    print(result)
    result.to_csv(f"data/sql_results/query_{number}.csv", index=False)
    sql_file.write(f"-- {title}\n{sql.strip()};\n\n")

sql_file.close()
conn.close()
print("\nPIPELINE COMPLETED")