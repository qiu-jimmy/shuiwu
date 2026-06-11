-- Add prepay_id column to orders table for WeChat Pay integration
-- Migration: 011_add_prepay_id_to_orders.sql
-- Description: Adds prepay_id column to store WeChat Pay prepay_id

-- Add prepay_id column to orders table
ALTER TABLE business.orders
ADD COLUMN IF NOT EXISTS prepay_id VARCHAR(64);

-- Add comment for the new column
COMMENT ON COLUMN business.orders.prepay_id IS '预支付交易会话标识 (WeChat Pay prepay_id)';

-- Create index for prepay_id (useful for payment status queries)
CREATE INDEX IF NOT EXISTS idx_orders_prepay_id ON business.orders(prepay_id);
