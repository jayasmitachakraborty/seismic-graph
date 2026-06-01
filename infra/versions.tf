terraform {
  required_version = ">= 1.5.0"

  required_providers {
    neo4jaura = {
      source  = "neo4j-labs/neo4jaura"
      version = "0.0.2-beta"
    }
  }
}
