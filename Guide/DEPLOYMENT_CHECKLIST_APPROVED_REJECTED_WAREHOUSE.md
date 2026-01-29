# Deployment Checklist: Approved/Rejected Warehouse Feature

**Feature**: Separate warehouse designation for approved and rejected quantities  
**Release Date**: January 28, 2026  
**Status**: Ready for Deployment  

---

## Pre-Deployment

### Code Review
- [ ] All Python code reviewed for syntax errors
- [ ] All JavaScript code reviewed for logic errors
- [ ] All HTML markup validated
- [ ] No console errors in browser
- [ ] No linting warnings

### Testing
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Manual testing completed
- [ ] Edge cases tested
- [ ] Error handling verified

### Documentation
- [ ] Implementation guide completed
- [ ] Quick start guide completed
- [ ] API documentation updated
- [ ] Database migration documented
- [ ] Troubleshooting guide created

---

## Database Migration

### Pre-Migration
- [ ] Database backup created
  ```bash
  mysqldump -u [user] -p [database] > backup_$(date +%Y%m%d_%H%M%S).sql
  ```
- [ ] Backup verified (can restore if needed)
- [ ] Maintenance window scheduled
- [ ] Stakeholders notified

### Migration Execution
- [ ] Stop application
  ```bash
  sudo systemctl stop grpo-app
  # or
  docker-compose down
  ```
- [ ] Apply migration
  ```bash
  mysql -u [user] -p [database] < migrations/mysql/changes/2026-01-28_grpo_transfer_approved_rejected_warehouse.sql
  ```
- [ ] Verify migration success
  ```sql
  DESCRIBE grpo_transfer_items;
  -- Check for new columns:
  -- approved_to_warehouse
  -- approved_to_bin_code
  -- approved_to_bin_abs_entry
  -- rejected_to_warehouse
  -- rejected_to_bin_code
  -- rejected_to_bin_abs_entry
  ```
- [ ] Verify indexes created
  ```sql
  SHOW INDEXES FROM grpo_transfer_items;
  -- Check for:
  -- idx_approved_to_warehouse
  -- idx_rejected_to_warehouse
  ```

### Post-Migration
- [ ] No errors in migration log
- [ ] Database integrity verified
- [ ] Existing data preserved
- [ ] New columns populated with NULL (expected)

---

## Code Deployment

### File Deployment
- [ ] Copy updated files to production:
  - [ ] `modules/grpo_transfer/models.py`
  - [ ] `modules/grpo_transfer/routes.py`
  - [ ] `modules/grpo_transfer/templates/grpo_transfer/session_detail.html`

### Application Restart
- [ ] Start application
  ```bash
  sudo systemctl start grpo-app
  # or
  docker-compose up -d
  ```
- [ ] Verify application started successfully
- [ ] Check application logs for errors
- [ ] Verify no startup errors

### Health Check
- [ ] Application responds to requests
- [ ] Database connection working
- [ ] SAP B1 connection working
- [ ] All endpoints accessible

---

## Functional Testing

### UI Testing
- [ ] Open GRPO Transfer session
- [ ] Click Edit on an item
- [ ] Verify new warehouse sections appear
- [ ] Verify "Approved Qty Designation" section visible (green)
- [ ] Verify "Rejected Qty Designation" section visible (red)

### Field Enabling/Disabling
- [ ] Enter Approved Qty = 100
  - [ ] Approved warehouse fields enable
  - [ ] Rejected warehouse fields disable
- [ ] Enter Rejected Qty = 50
  - [ ] Rejected warehouse fields enable
- [ ] Set both to 0
  - [ ] Both warehouse sections disable
- [ ] Set both > 0
  - [ ] Both warehouse sections enable

### Warehouse Selection
- [ ] Click Approved warehouse dropdown
  - [ ] Warehouses load correctly
  - [ ] Can select warehouse
- [ ] Warehouse change triggers bin loading
  - [ ] Bin codes load for selected warehouse
  - [ ] Can select bin code
- [ ] Repeat for Rejected warehouse

### Validation
- [ ] Try to save with both quantities = 0
  - [ ] Error: "At least one quantity must be > 0"
- [ ] Try to save with Approved Qty > 0 but no warehouse
  - [ ] Error: "Please select a destination warehouse for approved quantity"
- [ ] Try to save with Rejected Qty > 0 but no warehouse
  - [ ] Error: "Please select a destination warehouse for rejected quantity"
- [ ] Save with valid data
  - [ ] Success message appears
  - [ ] Modal closes
  - [ ] Page refreshes

### Transfer Posting
- [ ] Click "Post to SAP B1"
- [ ] Transfer preview modal appears
- [ ] Shows approved and rejected sections
- [ ] Click "Confirm & Post to SAP B1"
- [ ] Approved transfer posts successfully
- [ ] Rejected transfer posts successfully
- [ ] Success message shows both SAP doc numbers
- [ ] Session status changes to "transferred"

### Batch Items
- [ ] Edit batch-managed item
- [ ] Verify batch information displays
- [ ] Set approved and rejected quantities
- [ ] Post transfer
- [ ] Verify batch numbers included in SAP transfer

### Non-Batch Items
- [ ] Edit non-batch item
- [ ] Verify no batch information displays
- [ ] Set approved and rejected quantities
- [ ] Post transfer
- [ ] Verify empty BatchNumbers array in SAP transfer

---

## SAP B1 Verification

### Approved Transfer
- [ ] Stock Transfer document created
- [ ] Document number recorded
- [ ] From Warehouse: Correct (source)
- [ ] To Warehouse: Correct (approved warehouse)
- [ ] Line items: Correct quantities
- [ ] Batch numbers: Correct (if batch item)
- [ ] Bin allocations: Correct (if bins designated)

### Rejected Transfer
- [ ] Stock Transfer document created
- [ ] Document number recorded
- [ ] From Warehouse: Correct (source)
- [ ] To Warehouse: Correct (rejected warehouse)
- [ ] Line items: Correct quantities
- [ ] Batch numbers: Correct (if batch item)
- [ ] Bin allocations: Correct (if bins designated)

### Document Integrity
- [ ] Both documents have correct DocDate
- [ ] Comments field populated correctly
- [ ] BaseEntry and BaseLine correct
- [ ] BaseType = "PurchaseDeliveryNotes"

---

## Audit & Logging

### Session Audit Log
- [ ] Approved transfer logged
  - [ ] Action: "transferred_approved"
  - [ ] Description: Contains SAP doc numbers
  - [ ] User: Correct user recorded
  - [ ] Timestamp: Correct
- [ ] Rejected transfer logged
  - [ ] Action: "transferred_rejected"
  - [ ] Description: Contains SAP doc numbers
  - [ ] User: Correct user recorded
  - [ ] Timestamp: Correct

### Application Logs
- [ ] No error messages
- [ ] No warning messages
- [ ] API calls logged correctly
- [ ] SAP B1 responses logged

---

## Backward Compatibility

### Existing Sessions
- [ ] Open existing session (created before deployment)
- [ ] Edit item
- [ ] Verify old "To Warehouse" field still works
- [ ] Save changes
- [ ] Post transfer
- [ ] Verify transfer posts successfully

### Legacy Data
- [ ] Query database for items with old warehouse data
  ```sql
  SELECT * FROM grpo_transfer_items WHERE to_warehouse IS NOT NULL;
  ```
- [ ] Verify data preserved
- [ ] Verify new columns NULL (expected)

---

## Performance Testing

### Load Testing
- [ ] Open multiple sessions simultaneously
- [ ] Edit multiple items
- [ ] Verify no performance degradation
- [ ] Check database query performance
- [ ] Monitor API response times

### Database Performance
- [ ] Query with new indexes
  ```sql
  SELECT * FROM grpo_transfer_items WHERE approved_to_warehouse = '7000-QFG';
  ```
- [ ] Verify index used (EXPLAIN plan)
- [ ] Response time acceptable

---

## User Communication

### Notifications
- [ ] Notify users of new feature
- [ ] Provide quick start guide
- [ ] Provide troubleshooting guide
- [ ] Schedule training session (if needed)

### Documentation
- [ ] Update user manual
- [ ] Update API documentation
- [ ] Update system architecture diagram
- [ ] Update database schema documentation

---

## Rollback Plan

### If Issues Occur
- [ ] Stop application
- [ ] Restore database from backup
  ```bash
  mysql -u [user] -p [database] < backup_YYYYMMDD_HHMMSS.sql
  ```
- [ ] Revert code changes
- [ ] Restart application
- [ ] Verify rollback successful

### Rollback Testing
- [ ] Test rollback procedure
- [ ] Verify backup can be restored
- [ ] Verify application starts after rollback
- [ ] Verify data integrity after rollback

---

## Post-Deployment

### Monitoring (First 24 Hours)
- [ ] Monitor application logs
- [ ] Monitor database performance
- [ ] Monitor SAP B1 integration
- [ ] Monitor user feedback
- [ ] Check for any errors or issues

### Monitoring (First Week)
- [ ] Review audit logs
- [ ] Check transfer success rate
- [ ] Monitor API response times
- [ ] Verify no data corruption
- [ ] Collect user feedback

### Sign-Off
- [ ] QA sign-off: ✅
- [ ] DBA sign-off: ✅
- [ ] Product owner sign-off: ✅
- [ ] Operations sign-off: ✅

---

## Deployment Summary

| Item | Status | Notes |
|------|--------|-------|
| Database Migration | ⏳ Pending | Apply before code deployment |
| Code Deployment | ⏳ Pending | 3 files to deploy |
| Application Restart | ⏳ Pending | Verify startup logs |
| Functional Testing | ⏳ Pending | All scenarios must pass |
| SAP B1 Verification | ⏳ Pending | Verify both transfer types |
| Backward Compatibility | ⏳ Pending | Test with existing sessions |
| Performance Testing | ⏳ Pending | Monitor for degradation |
| User Communication | ⏳ Pending | Notify users of changes |

---

## Deployment Timeline

**Estimated Duration**: 2-3 hours

| Phase | Duration | Tasks |
|-------|----------|-------|
| Pre-Deployment | 30 min | Backup, notify stakeholders |
| Database Migration | 15 min | Apply migration, verify |
| Code Deployment | 15 min | Copy files, restart app |
| Testing | 60 min | Functional, SAP B1, backward compat |
| Monitoring | 30 min | Check logs, verify stability |

---

## Contact Information

**For Issues During Deployment**:
- Database: [DBA Contact]
- Application: [Dev Lead Contact]
- SAP B1: [SAP Admin Contact]
- Product: [Product Owner Contact]

---

## Approval Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| QA Lead | __________ | __________ | __________ |
| DBA | __________ | __________ | __________ |
| Dev Lead | __________ | __________ | __________ |
| Product Owner | __________ | __________ | __________ |
| Operations | __________ | __________ | __________ |

---

## Deployment Completed

- [ ] All checklist items completed
- [ ] All tests passing
- [ ] All approvals obtained
- [ ] Feature deployed to production
- [ ] Users notified
- [ ] Monitoring active

**Deployment Date**: __________  
**Deployed By**: __________  
**Verified By**: __________  

---

## Post-Deployment Notes

```
[Space for deployment notes and observations]
```

---

**Document Version**: 1.0  
**Last Updated**: January 28, 2026  
**Status**: Ready for Deployment
