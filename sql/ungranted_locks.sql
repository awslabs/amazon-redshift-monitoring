select count(*) from svv_transactions t WHERE t.granted = 'f' and t.pid != pg_backend_pid();
