select count(*) from svv_transactions t WHERE t.lockable_object_type = 'transactionid' and pid != pg_backend_pid();
