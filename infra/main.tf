provider "neo4jaura" {
  # Both values are sourced from the gitignored .env file via:
  #   set -a; source .env; set +a
  # which exports TF_VAR_aura_client_id and TF_VAR_aura_client_secret.
  client_id     = var.aura_client_id
  client_secret = var.aura_client_secret
}

module "neo4j" {
  source         = "./modules/neo4j"
  graph_name     = var.neo4j_graph_name
  region         = var.neo4j_region
  cloud_provider = var.neo4j_cloud_provider
  instance_type  = var.neo4j_instance_type
}
