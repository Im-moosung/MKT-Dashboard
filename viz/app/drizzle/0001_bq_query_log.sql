CREATE TABLE "bq_query_log" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" uuid,
	"dashboard_id" uuid,
	"query_hash" varchar(64) NOT NULL,
	"estimated_bytes" bigint DEFAULT 0 NOT NULL,
	"actual_bytes" bigint,
	"status" varchar(16) NOT NULL,
	"error" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "bq_query_log" ADD CONSTRAINT "bq_query_log_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "bq_query_log" ADD CONSTRAINT "bq_query_log_dashboard_id_dashboards_id_fk" FOREIGN KEY ("dashboard_id") REFERENCES "public"."dashboards"("id") ON DELETE cascade ON UPDATE no action;
