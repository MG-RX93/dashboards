# Finance Dashboard Documentation

## Overview
A comprehensive finance dashboard that provides insights into credit transaction patterns, spending habits, and financial trends.

## Panels

### 1. Monthly Growth Rate 2
**Panel Type**: Time Series  
**Size**: 10x8  
**Description**: Shows month-over-month growth rate in spending

**Query**:
```sql
WITH monthly_expenses AS (
    SELECT 
        DATE_TRUNC('month', transaction_date) as month,
        ABS(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)) as total_expenses
    FROM credit_transactions
    WHERE $__timeFilter(transaction_date)
    GROUP BY DATE_TRUNC('month', transaction_date)
),
growth_calc AS (
    SELECT 
        month,
        CASE 
            WHEN LAG(total_expenses) OVER (ORDER BY month) = 0 
                OR LAG(total_expenses) OVER (ORDER BY month) IS NULL 
            THEN 0 
            ELSE ROUND(
                ((total_expenses - LAG(total_expenses) OVER (ORDER BY month)) 
                / LAG(total_expenses) OVER (ORDER BY month) * 100)::numeric, 
                2
            )
        END as growth_rate
    FROM monthly_expenses
)
SELECT 
    month as time,
    growth_rate as "Growth Rate %"
FROM growth_calc
ORDER BY month;
```

**Visualization Settings**:
- Line chart with points
- 10% fill opacity
- Linear interpolation
- Classic color palette
- Point size: 7px
- Line width: 2px

### 2. Monthly Expense Growth Rate
**Panel Type**: Time Series  
**Size**: 14x8  
**Description**: Month-over-month spending change showing total expenses, previous month expenses, and growth rate

**Query**:
```sql
WITH monthly_expenses AS (
    SELECT 
        DATE_TRUNC('month', transaction_date) as month,
        ABS(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)) as total_expenses
    FROM credit_transactions
    WHERE $__timeFilter(transaction_date)
    GROUP BY DATE_TRUNC('month', transaction_date)
),
growth_calc AS (
    SELECT 
        month,
        total_expenses,
        LAG(total_expenses) OVER (ORDER BY month) as prev_month_expenses,
        CASE 
            WHEN LAG(total_expenses) OVER (ORDER BY month) = 0 
                OR LAG(total_expenses) OVER (ORDER BY month) IS NULL 
            THEN 0
            ELSE ROUND(
                ((total_expenses - LAG(total_expenses) OVER (ORDER BY month)) / 
                LAG(total_expenses) OVER (ORDER BY month) * 100)::numeric,
                2
            )
        END as growth_rate
    FROM monthly_expenses
)
SELECT 
    month as time,
    total_expenses as "Total Expenses",
    prev_month_expenses as "Previous Month Expenses",
    growth_rate as "Growth Rate %"
FROM growth_calc
ORDER BY month;
```

**Visualization Settings**:
- Line chart with always visible points
- 10% fill opacity
- Point size: 5px
- Line width: 2px
- Axis border shown

### 3. Transaction Activity Heatmap
**Panel Type**: Bar Gauge  
**Size**: 11x11  
**Description**: Spending patterns by day of week

**Query**:
```sql
WITH day_metrics AS (
    SELECT 
        EXTRACT('dow' FROM transaction_date::timestamp) as dow,
        ABS(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)) as total_spending
    FROM credit_transactions
    WHERE 
        $__timeFilter(transaction_date)
        AND amount < 0
    GROUP BY 
        EXTRACT('dow' FROM transaction_date::timestamp)
),
day_names AS (
    SELECT 
        dow,
        name
    FROM (
        VALUES 
            (0, 'Sunday Total Spending'),
            (1, 'Monday Total Spending'),
            (2, 'Tuesday Total Spending'),
            (3, 'Wednesday Total Spending'),
            (4, 'Thursday Total Spending'),
            (5, 'Friday Total Spending'),
            (6, 'Saturday Total Spending')
    ) AS v(dow, name)
)
SELECT 
    dn.name as metric,
    dm.total_spending as value    
FROM day_names dn
LEFT JOIN day_metrics dm ON dn.dow = dm.dow
ORDER BY dm.total_spending DESC;
```

**Visualization Settings**:
- LCD display mode
- Horizontal orientation
- Green-Yellow-Red color scheme
- Auto sizing

### 4. Credit Card Usage Distribution
**Panel Type**: Pie Chart  
**Size**: 13x11  
**Description**: Distribution of spending across different credit cards

**Query**:
```sql
SELECT
    credit_card_name,
    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as "Total Spending"
FROM credit_transactions
WHERE
    transaction_date >= $__timeFrom()
    AND transaction_date < $__timeTo()
GROUP BY credit_card_name
ORDER BY "Total Spending" DESC;
```

**Visualization Settings**:
- Display labels: name
- Legend: Right-aligned table
- Show values: percent and absolute
- USD currency unit

### 5. Spending by Category
**Panel Type**: Pie Chart  
**Size**: 24x18  
**Description**: Distribution of spending across different categories

**Query**:
```sql
SELECT
    category,
    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as "Total Spending"
FROM credit_transactions
WHERE
    transaction_date >= $__timeFrom()
    AND transaction_date < $__timeTo()
GROUP BY category
ORDER BY "Total Spending" DESC;
```

**Visualization Settings**:
- Display labels: name
- Legend: Right-aligned table with sorting
- Show values: percent and absolute
- USD currency unit
- Transparent background

### 6. Monthly Spending Bar Chart
**Panel Type**: Bar Chart  
**Size**: 24x9  
**Description**: Monthly spending totals displayed as bars

**Query**:
```sql
SELECT
    DATE_TRUNC('month', transaction_date) as time,
    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as "Monthly Spending"
FROM credit_transactions
WHERE
    transaction_date >= $__timeFrom()
    AND transaction_date < $__timeTo()
GROUP BY DATE_TRUNC('month', transaction_date)
ORDER BY time;
```

**Visualization Settings**:
- Vertical orientation
- Bar width: 97%
- Group width: 70%
- Show values: auto
- USD currency unit
- Classic color palette
- 80% fill opacity

### 7. Cumulative Spending Trend
**Panel Type**: Time Series  
**Size**: 24x8  
**Description**: Running total of spending over time

**Query**:
```sql
WITH monthly_spending AS (
    SELECT 
        DATE_TRUNC('month', transaction_date) as time,
        SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as month_total
    FROM credit_transactions
    WHERE
        transaction_date >= $__timeFrom()
        AND transaction_date < $__timeTo()
    GROUP BY DATE_TRUNC('month', transaction_date)
)
SELECT 
    time,
    SUM(month_total) OVER (ORDER BY time) as "Cumulative Spending"
FROM monthly_spending
ORDER BY time;
```

**Visualization Settings**:
- Line chart
- No fill opacity
- Line width: 3px
- Point size: 5px
- USD currency unit
- Transparent background

## Time Range
- Default time range: 2024-01-01 to 2024-12-22
- Timezone: Browser local time

## Dashboard Settings
- Editable: Yes
- Refresh: Manual
- Description: "One pane to everything finance"
- Version: 9
- UID: fe8czjofzhdz4d