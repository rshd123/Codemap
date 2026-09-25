from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    llm_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"

    github_api_url: str = "https://api.github.com"
    github_token: str = ""
    osv_api_url: str = "https://api.osv.dev"
    nvd_api_url: str = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    nvd_api_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
