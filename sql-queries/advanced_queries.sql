-- ============================================================================
-- QUERY #1: Simple Customer Analysis
-- ============================================================================
-- 
-- WHAT THIS DOES:
-- Analyze customer spending patterns and identify important customers
--

SELECT
    c.customer_id,
    c.customer_name,
    c.email,
    -- Count how many purchases each customer made
    COUNT(DISTINCT o.order_id) as total_purchases,
    -- Sum of all money they spent
    SUM(oi.quantity * oi.unit_price) as total_spent,
    -- Average amount spent per order
    ROUND(AVG(oi.quantity * oi.unit_price), 2) as avg_per_order,
    -- When was their last purchase
    MAX(o.order_date) as last_purchase_date,
    -- How many days since their last purchase
    DATEDIFF(day, MAX(o.order_date), CURRENT_DATE) as days_since_purchase,
    -- Simple customer type
    CASE
        WHEN SUM(oi.quantity * oi.unit_price) > 5000 THEN 'VIP'
        WHEN SUM(oi.quantity * oi.unit_price) > 1000 THEN 'Regular'
        ELSE 'New/Occasional'
    END as customer_type,
    -- Risk of losing this customer
    CASE
        WHEN DATEDIFF(day, MAX(o.order_date), CURRENT_DATE) > 180 THEN 'High Risk'
        WHEN DATEDIFF(day, MAX(o.order_date), CURRENT_DATE) > 90 THEN 'Medium Risk'
        ELSE 'Active'
    END as customer_status
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
LEFT JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_date >= CURRENT_DATE - INTERVAL '24 months'
GROUP BY c.customer_id, c.customer_name, c.email
ORDER BY total_spent DESC;


-- ============================================================================
-- QUERY #2: Simple Product Performance
-- ============================================================================
--
-- WHAT THIS DOES:
-- Track how well each product is selling over time
--

SELECT
    DATE(o.order_date) as sale_date,
    p.product_id,
    p.product_name,
    p.category,
    -- Total units sold that day
    SUM(oi.quantity) as units_sold,
    -- Total revenue that day
    SUM(oi.quantity * oi.unit_price) as daily_revenue,
    -- Average price per unit
    ROUND(AVG(oi.unit_price), 2) as avg_price,
    -- Simple performance label
    CASE
        WHEN SUM(oi.quantity * oi.unit_price) > 1000 THEN 'Best Seller'
        WHEN SUM(oi.quantity * oi.unit_price) > 100 THEN 'Good Seller'
        ELSE 'Low Volume'
    END as performance_level
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE o.order_date >= CURRENT_DATE - INTERVAL '365 days'
GROUP BY DATE(o.order_date), p.product_id, p.product_name, p.category
ORDER BY sale_date DESC, daily_revenue DESC;
