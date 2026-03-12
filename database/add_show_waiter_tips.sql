-- Add show_waiter_tips column to hotel_modules table
-- This controls whether waiters can see their tip amounts on the Waiter Dashboard

ALTER TABLE hotel_modules 
ADD COLUMN IF NOT EXISTS show_waiter_tips BOOLEAN DEFAULT TRUE;

-- If the column already exists, this will have no effect
-- Default is TRUE so existing hotels will continue to show tips to waiters
