-- Add separate warehouse/bin columns for approved and rejected quantities
-- Migration Date: 2026-01-28

ALTER TABLE grpo_transfer_items ADD COLUMN approved_to_warehouse VARCHAR(50) NULL AFTER from_bin_abs_entry;
ALTER TABLE grpo_transfer_items ADD COLUMN approved_to_bin_code VARCHAR(100) NULL AFTER approved_to_warehouse;
ALTER TABLE grpo_transfer_items ADD COLUMN approved_to_bin_abs_entry INT NULL AFTER approved_to_bin_code;

ALTER TABLE grpo_transfer_items ADD COLUMN rejected_to_warehouse VARCHAR(50) NULL AFTER approved_to_bin_abs_entry;
ALTER TABLE grpo_transfer_items ADD COLUMN rejected_to_bin_code VARCHAR(100) NULL AFTER rejected_to_warehouse;
ALTER TABLE grpo_transfer_items ADD COLUMN rejected_to_bin_abs_entry INT NULL AFTER rejected_to_bin_code;

-- Add indexes for performance
CREATE INDEX idx_approved_to_warehouse ON grpo_transfer_items(approved_to_warehouse);
CREATE INDEX idx_rejected_to_warehouse ON grpo_transfer_items(rejected_to_warehouse);
