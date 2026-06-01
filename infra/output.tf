output "neo4j_connection_url" {
  value       = module.neo4j.connection_url
  description = "The Bolt connection URL for your database"
}

output "neo4j_region" {
  value       = var.neo4j_region
  description = "Neo4j instance  region"
}

output "neo4j_username" {
  value       = module.neo4j.username
  description = "The default administrator username"
}

output "neo4j_password" {
  value       = module.neo4j.password
  description = "The automatically generated password for the instance"
  sensitive   = true
}
