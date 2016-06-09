SELECT service_class, num_queued_queries, num_executing_queries from stv_wlm_service_class_state w WHERE w.service_class >= 6 ORDER BY 1;
