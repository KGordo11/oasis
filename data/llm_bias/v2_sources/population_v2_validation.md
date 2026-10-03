# Population v2: target vs the 100 users

Built by `build_population_v2.py`, seed 20261002. Targets = Census 2024 adults weighted by Pew 2025 social media use by age, except where noted.

| Attribute | Target % | Users (of 100) |
|---|---|---|
| age 18-29 | 22.5 | 23 |
| age 30-49 | 36.6 | 36 |
| age 50-64 | 23.5 | 24 |
| age 65-+ | 17.4 | 17 |
| female | 50.8 | 50 |
| male | 49.2 | 50 |
| region Northeast | 17.3 | 19 |
| region Midwest | 20.4 | 21 |
| region South | 38.7 | 39 |
| region West | 23.6 | 21 |
| rural (Census 2020, by state) | 19.9 | 20 |

Education (Census CPS 2024, matched within age group and sex):

| Education | Users |
|---|---|
| less than high school | 5 |
| high school diploma | 31 |
| some college, no degree | 17 |
| associate degree | 7 |
| bachelor's degree | 27 |
| graduate degree | 13 |

Work (BLS CPS 2025 employment ratio by age and sex; BLS OEWS 2024 job groups):

| Work | Users |
|---|---|
| not currently working | 17 |
| retired | 15 |
| college student | 7 |
| works in office and administrative support | 7 |
| works in transportation and material moving | 5 |
| works in food preparation and serving | 5 |
| works in sales | 5 |
| works in management | 4 |
| works in education (teaching and libraries) | 4 |
| works in production and manufacturing | 4 |
| works in healthcare (doctors, nurses, technicians) | 4 |
| works in business and financial operations | 4 |
| works in construction | 3 |
| works in healthcare support | 3 |
| works in installation, maintenance and repair | 2 |
| works in building and grounds cleaning and maintenance | 2 |
| works in computers and math | 2 |
| works in protective services | 1 |
| works in life, physical and social science | 1 |
| works in architecture and engineering | 1 |
| works in personal care and service | 1 |
| works in legal | 1 |
| works in arts, design, entertainment, sports and media | 1 |
| works in community and social services | 1 |

Topic stances: every topic has exactly 20 users at each stance; every pair of topics has each of the 25 stance combinations exactly 4 times (zero correlation).

SHA-256 of personas_v2.json content: `11ac527c6351e054dc2e054f3de892893404d58df1eb7eb32a0104a36a2f6383`
