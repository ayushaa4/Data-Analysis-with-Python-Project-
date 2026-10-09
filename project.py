
# Import Libraries

import pandas as pd
import matplotlib.pyplot as plt


# Load Dataset

df = pd.read_csv("breweries.csv")

print("First 5 rows:")
print(df.head())

print("\nDataset shape:")
print(df.shape)

print("\nColumn names:")
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

# Remove duplicate rows
df_clean = df_clean.drop_duplicates()

# Remove extra spaces from text columns
text_columns = df_clean.select_dtypes(include="object").columns

for col in text_columns:
    df_clean[col] = df_clean[col].str.strip()

# Replace empty strings with missing values
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