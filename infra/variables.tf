variable "aura_client_id" {
  type        = string
  sensitive   = true
  description = "Aura API client_id. Set via TF_VAR_aura_client_id (sourced from .env)."
}

variable "aura_client_secret" {
  type        = string
  sensitive   = true
  description = "Aura API client_secret. Set via TF_VAR_aura_client_secret (sourced from .env)."
}

variable "neo4j_graph_name" {
  type        = string
  default     = "seismic-graph"
  description = "Name of the AuraDB instance"
}

variable "neo4j_region" {
  type        = string
  default     = "us-central1"
  description = "Region for the AuraDB instance. Note: free-db is only available in certain regions (e.g. us-central1 on GCP)."
}

variable "neo4j_cloud_provider" {
  type        = string
  default     = "gcp"
  description = "Cloud provider for the AuraDB instance. One of [gcp, aws, azure]."
}

variable "neo4j_instance_type" {
  type        = string
  default     = "free-db"
  description = "AuraDB instance type. One of [free-db, professional-db, enterprise-db, professional-ds, enterprise-ds, business-critical]."
}
