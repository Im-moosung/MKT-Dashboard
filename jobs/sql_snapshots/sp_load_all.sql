BEGIN
  DECLARE v_run_id STRING DEFAULT GENERATE_UUID();
  DECLARE v_start_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP();

  INSERT INTO `your-gcp-project-id.ops.etl_run_log` (
    run_id, pipeline_name, source_name, started_at, ended_at, status,
    rows_read, rows_written, error_message, metadata
  )
  VALUES (
    v_run_id, 'warehouse_v2', 'all', v_start_ts, NULL, 'RUNNING',
    NULL, NULL, NULL, JSON_OBJECT('start_date', CAST(p_start_date AS STRING), 'end_date', CAST(p_end_date AS STRING))
  );

  BEGIN
    CALL `your-gcp-project-id.ops.sp_load_stg`(p_start_date, p_end_date);
    CALL `your-gcp-project-id.ops.sp_load_core`(p_start_date, p_end_date);
    CALL `your-gcp-project-id.ops.sp_load_asset_stg`(p_start_date, p_end_date);
    CALL `your-gcp-project-id.ops.sp_load_asset_core`(p_start_date, p_end_date);
    CALL `your-gcp-project-id.ops.sp_load_breakdown_stg`(p_start_date, p_end_date);
    CALL `your-gcp-project-id.ops.sp_load_breakdown_core`(p_start_date, p_end_date);
    CALL `your-gcp-project-id.ops.sp_enrich_branch_id`(p_start_date, p_end_date);

    UPDATE `your-gcp-project-id.ops.etl_run_log`
    SET ended_at = CURRENT_TIMESTAMP(),
        status = 'SUCCESS'
    WHERE run_id = v_run_id
      AND DATE(started_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY);
  EXCEPTION WHEN ERROR THEN
    UPDATE `your-gcp-project-id.ops.etl_run_log`
    SET ended_at = CURRENT_TIMESTAMP(),
        status = 'FAILED',
        error_message = @@error.message
    WHERE run_id = v_run_id
      AND DATE(started_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY);
    RAISE;
  END;
END