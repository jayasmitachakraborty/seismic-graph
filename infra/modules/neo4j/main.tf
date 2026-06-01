variable "graph_name" {
  type        = string
  description = "Name of the AuraDB instance"
}

variable "region" {
  type        = string
  description = "Region for the AuraDB instance"
}

variable "cloud_provider" {
  type        = string
  default     = "gcp"
  description = "Cloud provider for the AuraDB instance. One of [gcp, aws, azure]."
}

variable "instance_type" {
  type        = string
  default     = "free-db"
  description = "AuraDB instance type."
}

# Pull the Aura project (a.k.a. tenant) id for the credentials in use.
# The free-db tier is created against the default project of the Aura account.
data "neo4jaura_projects" "this" {}

resource "neo4jaura_instance" "seismic_graph" {
  name           = var.graph_name
  region         = var.region
  cloud_provider = var.cloud_provider
  type           = var.instance_type
  project_id     = data.neo4jaura_projects.this.projects[0].id
}

output "connection_url" {
  value       = neo4jaura_instance.seismic_graph.connection_url
  description = "Bolt connection URL for the AuraDB instance"
}

output "username" {
  value       = neo4jaura_instance.seismic_graph.username
  description = "Default admin username"
}

output "password" {
  value       = neo4jaura_instance.seismic_graph.password
  description = "Auto-generated password for the AuraDB instance"
  sensitive   = true
}
