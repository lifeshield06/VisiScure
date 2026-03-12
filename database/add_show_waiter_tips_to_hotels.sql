-- Add show_waiter_tips column to hotels table
-- This controls whether waiters can see their tip amounts on the Waiter Dashboard

ALTER TABLE hotels 
ADD COLUMN IF NOT EXISTS show_waiter_tips TINYINT DEFAULT 1;

-- Default to 1 (visible) for existing hotels
UPDATE hotels SET show_waiter_tips = 1 WHERE show_waiter_tips IS NULL;
