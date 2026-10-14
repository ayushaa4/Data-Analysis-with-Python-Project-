
# Import Libraries

import pandas as pd
import matplotlib.pyplot as plt
import requests


# Load Dataset

df = pd.read_csv("breweries.csv")

print("First 5 Rows:")
print(df.head())

print("\nDataset Shape:")
print(df.shape)

print("\nColumn Names:")
print(df.columns.tolist())


# Explore Dataset

print("\nDataset Information:")
df.info()

print("\nStatistical Summary:")
print(df.describe(include="all"))

print("\nMissing Values:")
print(df.isnull().sum())

print("\nDuplicate Rows:")
print(df.duplicated().sum())


# Clean Dataset

df_clean = df.copy()

df_clean = df_clean.drop_duplicates()

text_columns = df_clean.select_dtypes(include="object").columns

for col in text_columns:
    df_clean[col] = df_clean[col].str.strip()

df_clean[text_columns] = df_clean[text_columns].replace(
    "", pd.NA
)

print("\nShape After Cleaning:")
print(df_clean.shape)

print("\nMissing Values After Cleaning:")
print(df_clean.isnull().sum())


# Analyze Brewery Types

print("\nBrewery Types:")
brewery_types = df_clean["brewery_type"].value_counts()
print(brewery_types)

print("\nTop 5 Brewery Types:")
print(brewery_types.head(5))


# Analyze Countries

print("\nBreweries by Country:")
country_counts = df_clean["country"].value_counts()
print(country_counts)

print("\nTop 10 Countries by Brewery Count:")
print(country_counts.head(10))


# Analyze Cities

print("\nTop 10 Cities by Brewery Count:")
city_counts = df_clean["city"].value_counts()
print(city_counts.head(10))


# Visualize Brewery Types

brewery_types.plot(kind="bar", figsize=(9, 5))

plt.title("Number of Breweries by Type")
plt.xlabel("Brewery Type")
plt.ylabel("Number of Records")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()


# Visualize Top 10 Countries

country_counts.head(10).plot(kind="bar", figsize=(10, 5))

plt.title("Top 10 Countries by Number of Breweries")
plt.xlabel("Country")
plt.ylabel("Number of Records")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()


# Analyze Brewery Types by Country

print("\nBrewery Types by Country:")

type_country = pd.crosstab(
    df_clean["country"],
    df_clean["brewery_type"]
)

print(type_country.head(10))


# Analyze Missing Location Information

print("\nMissing City Information:")
print(df_clean["city"].isnull().sum())

print("\nMissing Country Information:")
print(df_clean["country"].isnull().sum())

print("\nMissing Latitude Information:")
print(df_clean["latitude"].isnull().sum())

print("\nMissing Longitude Information:")
print(df_clean["longitude"].isnull().sum())


# Analyze Website Information

website_count = df_clean["website_url"].notnull().sum()
no_website_count = df_clean["website_url"].isnull().sum()

print("\nBreweries with Website Information:")
print(website_count)

print("\nBreweries without Website Information:")
print(no_website_count)


# Visualize Website Information

website_data = pd.Series({
    "Has Website": website_count,
    "No Website": no_website_count
})

website_data.plot(kind="bar", figsize=(7, 4))

plt.title("Breweries with and without Websites")
plt.xlabel("Website Information")
plt.ylabel("Number of Breweries")
plt.xticks(rotation=0)
plt.tight_layout()
plt.show()


# Get Data from API

url = "https://api.openbrewerydb.org/v1/breweries"

try:
    response = requests.get(url, timeout=30)

    print("\nAPI Status Code:")
    print(response.status_code)

    if response.status_code == 200:
        api_data = response.json()
        api_df = pd.DataFrame(api_data)

        print("\nFirst 5 API Records:")
        print(api_df.head())

        print("\nAPI Dataset Shape:")
        print(api_df.shape)

    else:
        print("Failed to retrieve data from API.")

except requests.RequestException as error:
    print("\nAPI Request Error:")
    print(error)

# Compare CSV Data with API Data
csv_ids = set(df_clean["id"].dropna().astype(str).str.strip())
api_ids = api_df["id"].astype("string").str.strip()

api_df["found_in_csv"] = api_ids.isin(csv_ids)

print("\nAPI and CSV Comparison:")
print("Total API Records:", len(api_df))
print("API Records Found in CSV:", api_df["found_in_csv"].sum())
print("API Records Not Found in CSV:", (~api_df["found_in_csv"]).sum())

print("\nSample Comparison:")
print(api_df[["id", "name", "found_in_csv"]].head(10))