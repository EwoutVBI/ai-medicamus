-- Step 1: List all columns in fact and dimension tables
WITH ColumnsList AS (
    SELECT
        TABLE_NAME,
        COLUMN_NAME
    FROM
        INFORMATION_SCHEMA.COLUMNS
),
-- Step 2: Identify potential foreign key relationships based on common column names
PotentialRelationships AS (
    SELECT
        F.TABLE_NAME AS FactTable,
        F.COLUMN_NAME AS FactColumn,
        D.TABLE_NAME AS DimensionTable,
        D.COLUMN_NAME AS DimensionColumn
    FROM
        ColumnsList F
    JOIN
        ColumnsList D
    ON
        F.COLUMN_NAME = D.COLUMN_NAME
    WHERE
        F.TABLE_NAME LIKE 'Fct_%' AND D.TABLE_NAME LIKE 'Dim_%' AND F.COLUMN_NAME LIKE '%_Key%'
),
-- Step 3: Get other columns for each Fact table
OtherFactColumns AS (
    SELECT
        TABLE_NAME AS FactTable,
        STRING_AGG(COLUMN_NAME, ', ') AS OtherColumnsInFact
    FROM
        ColumnsList
    WHERE
        TABLE_NAME LIKE 'Fct_%'
    GROUP BY
        TABLE_NAME
),
-- Step 4: Get other columns for each Dimension table
OtherDimensionColumns AS (
    SELECT
        TABLE_NAME AS DimensionTable,
        STRING_AGG(COLUMN_NAME, ', ') AS OtherColumnsInDimension
    FROM
        ColumnsList
    WHERE
        TABLE_NAME LIKE 'Dim_%'
    GROUP BY
        TABLE_NAME
)
-- Step 5: Combine everything into the final result
SELECT
    PR.FactTable,
    PR.FactColumn,
    OFC.OtherColumnsInFact,
    PR.DimensionTable,
    PR.DimensionColumn,
    ODC.OtherColumnsInDimension
FROM
    PotentialRelationships PR
LEFT JOIN
    OtherFactColumns OFC ON PR.FactTable = OFC.FactTable
LEFT JOIN
    OtherDimensionColumns ODC ON PR.DimensionTable = ODC.DimensionTable
ORDER BY
    PR.FactTable,
    PR.FactColumn;
