
-- Initialize database with basic data

-- Insert default currencies
INSERT INTO currencies (code, name) VALUES 
    ('EUR', 'Euro'),
    ('USD', 'US Dollar'),
    ('JPY', 'Japanese Yen'),
    ('GBP', 'British Pound'),
    ('CAD', 'Canadian Dollar'),
    ('AUD', 'Australian Dollar'),
    ('CHF', 'Swiss Franc'),
    ('NZD', 'New Zealand Dollar')
ON CONFLICT (code) DO NOTHING;

-- Insert impact levels
INSERT INTO impact_levels (code, name, priority) VALUES 
    ('NON_ECONOMIC', 'Non-Economic', 0),
    ('LOW', 'Low Impact', 1),
    ('MEDIUM', 'Medium Impact', 2),
    ('HIGH', 'High Impact', 3)
ON CONFLICT (code) DO NOTHING;
