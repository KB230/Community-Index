# World Bank income groups - Data package

This data package contains the data that powers the chart ["World Bank income groups"](https://ourworldindata.org/grapher/world-bank-income-groups?v=1&csvType=full&useColumnShortNames=false) on the Our World in Data website. It was downloaded on July 28, 2026.

### Active Filters

A filtered subset of the full data was downloaded. The following filters were applied:

## CSV Structure

The high level structure of the CSV file is that each row is an observation for an entity (usually a country or region) and a timepoint (usually a year).

The first two columns in the CSV file are "Entity" and "Code". "Entity" is the name of the entity (e.g. "United States"). "Code" is the OWID internal entity code that we use if the entity is a country or region. For most countries, this is the same as the [iso alpha-3](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-3) code of the entity (e.g. "USA") - for non-standard countries like historical countries these are custom codes.

The third column is either "Year" or "Day". If the data is annual, this is "Year" and contains only the year as an integer. If the column is "Day", the column contains a date string in the form "YYYY-MM-DD".

The final column is the data column, which is the time series that powers the chart. If the CSV data is downloaded using the "full data" option, then the column corresponds to the time series below. If the CSV data is downloaded using the "only selected data visible in the chart" option then the data column is transformed depending on the chart type and thus the association with the time series might not be as straightforward.


## Metadata.json structure

The .metadata.json file contains metadata about the data package. The "charts" key contains information to recreate the chart, like the title, subtitle etc.. The "columns" key contains information about each of the columns in the csv, like the unit, timespan covered, citation for the data etc..

## About the data

Our World in Data is almost never the original producer of the data - almost all of the data we use has been compiled by others. If you want to re-use data, it is your responsibility to ensure that you adhere to the sources' license and to credit them correctly. Please note that a single time series may have more than one source - e.g. when we stich together data from different time periods by different producers or when we calculate per capita metrics using population data from a second source.

## Detailed information about the data


## World Bank's income classification
Income classification based on the country's income each year.
Last updated: July 1, 2026  
Next update: July 2027  
Date range: 1987–2025  


### How to cite this data

#### In-line citation
If you have limited space (e.g. in data visualizations), you can use this abbreviated in-line citation:  
World Bank (2026) – with minor processing by Our World in Data

#### Full citation
World Bank (2026) – with minor processing by Our World in Data. “World Bank's income classification – World Bank” [dataset]. World Bank, “Income Classifications” [original data].
Source: World Bank (2026) – with minor processing by Our World In Data

### What you should know about this data
- The World Bank creates a yearly classification of countries by income for all countries with a population over 30,000.
- This classification stays the same throughout the World Bank's fiscal year (from July 1 to June 30) even if the income data for a country changes.
- Low-income countries are those with a gross national income (GNI) per capita of $1,175 or less in 2025.
- Lower-middle-income countries are those with a GNI per capita between $1,176 and $4,635 in 2025.
- Upper-middle-income countries are those with a GNI per capita between $4,636 and $14,375 in 2025.
- High-income countries are those with a GNI per capita of more than $14,375 in 2025.
- When the World Bank lacks recent income data for a country, it can leave that country temporarily unclassified. Venezuela had no classification from 2021 to 2024, and Ethiopia had none in 2024.

### How is this data described by its producer - World Bank (2026)?
For the current 2027 fiscal year, low-income economies are defined as those with a GNI per capita, calculated using the [World Bank Atlas method](https://datahelpdesk.worldbank.org/knowledgebase/articles/378832-what-is-the-world-bank-atlas-method), of $1,175 or less in 2025; lower middle-income economies are those with a GNI per capita between $1,176 and $4,635; upper middle-income economies are those with a GNI per capita between $4,636 and $14,375; high-income economies are those with more than a GNI per capita of $14,375.

Please note: Regions in this table include economies at all income levels. The term country, used interchangeably with economy, does not imply political independence but refers to any territory for which authorities report separate social or economic statistics. Click [here](https://datahelpdesk.worldbank.org/knowledgebase/articles/378834-how-does-the-world-bank-classify-countries) for information about how the World Bank classifies countries.

### Source

#### World Bank – Income Classifications
Retrieved on: 2026-07-01  
Retrieved from: https://datahelpdesk.worldbank.org/knowledgebase/articles/906519-world-bank-country-and-lending-groups  


    