"""
Core configuration for Grape Backend.
Loads environment variables and provides app-wide settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ========================================
    # Application Settings
    # ========================================
    environment: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    log_level: str = "INFO"

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # ========================================
    # Google Cloud Platform
    # ========================================
    gcp_project_id: str = ""
    gcp_region: str = "us-central1"
    gcs_bucket_name: str = ""
    google_api_key: str = ""
    vertex_ai_location: str = "us-central1"
    use_secret_manager: bool = False

    # ========================================
    # GraphDB / SPARQL
    # ========================================
    kg_sparql_endpoint_url: str = ""
    ontologies_sparql_endpoint_url: str = ""
    graphdb_username: str = ""
    graphdb_password: str = ""

    # ========================================
    # LLM Providers
    # ========================================
    gemini_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    deepseek_api_key: str = ""
    ovhcloud_api_key: str = ""
    hf_token: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # ========================================
    # LangChain / LangSmith
    # ========================================
    langchain_api_key: str = ""
    langchain_tracing_v2: bool = True
    langchain_project: str = "grape-backend"
    langchain_endpoint: str = "https://api.smith.langchain.com"

    # ========================================
    # gen2kgbot Configuration
    # ========================================
    gen2kgbot_data_dir: str = "./data"
    kg_short_name: str = "default_kg"
    kg_full_name: str = "Default Knowledge Graph"
    embedding_model: str = "nomic-embed-text"
    embedding_provider: str = "local"

    # ========================================
    # MCP Pipelines
    # ========================================
    enable_semantic_finder: bool = True
    enable_neighbourhood_retriever: bool = True
    enable_multi_hop_explorer: bool = True
    enable_ontology_builder: bool = True
    enable_example_retriever: bool = True
    enable_federated_connector: bool = True
    enable_sparql_executor: bool = True
    enable_proof_engine: bool = True
    enable_reasoning_narrator: bool = True

    pipeline_cache_enabled: bool = True
    pipeline_cache_ttl: int = 3600


# Global settings instance
settings = Settings()
