"""
OLISTAY Configuration Management
Environment-based configuration for the recommendation server
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class ServerConfig:
    """Server configuration"""
    host: str = os.getenv('SERVER_HOST', '0.0.0.0')
    port: int = int(os.getenv('SERVER_PORT', '8080'))
    grpc_port: int = int(os.getenv('GRPC_PORT', '50051'))
    workers: int = int(os.getenv('WORKERS', '4'))
    debug: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    environment: str = os.getenv('ENVIRONMENT', 'development')


@dataclass
class DatabaseConfig:
    """Database configuration"""
    # PostgreSQL
    postgres_host: str = os.getenv('POSTGRES_HOST', 'localhost')
    postgres_port: int = int(os.getenv('POSTGRES_PORT', '5432'))
    postgres_db: str = os.getenv('POSTGRES_DB', 'olistay')
    postgres_user: str = os.getenv('POSTGRES_USER', 'postgres')
    postgres_password: str = os.getenv('POSTGRES_PASSWORD', '')

    # MongoDB
    mongo_uri: str = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
    mongo_db: str = os.getenv('MONGO_DB', 'olistay')

    # Redis
    redis_host: str = os.getenv('REDIS_HOST', 'localhost')
    redis_port: int = int(os.getenv('REDIS_PORT', '6379'))
    redis_db: int = int(os.getenv('REDIS_DB', '0'))
    redis_password: Optional[str] = os.getenv('REDIS_PASSWORD')

    # Elasticsearch
    elasticsearch_hosts: list = os.getenv('ELASTICSEARCH_HOSTS', 'localhost:9200').split(',')
    elasticsearch_user: Optional[str] = os.getenv('ELASTICSEARCH_USER')
    elasticsearch_password: Optional[str] = os.getenv('ELASTICSEARCH_PASSWORD')

    @property
    def postgres_url(self) -> str:
        """Build PostgreSQL connection URL"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


@dataclass
class RecommendationConfig:
    """Recommendation algorithm configuration"""
    # Scoring weights
    financial_weight: float = float(os.getenv('FINANCIAL_WEIGHT', '0.40'))
    location_weight: float = float(os.getenv('LOCATION_WEIGHT', '0.30'))
    lifestyle_weight: float = float(os.getenv('LIFESTYLE_WEIGHT', '0.30'))

    # Financial rules
    rent_to_income_ratio: float = float(os.getenv('RENT_TO_INCOME_RATIO', '0.30'))
    min_savings_ratio: float = float(os.getenv('MIN_SAVINGS_RATIO', '0.10'))

    # Recommendation limits
    max_recommendations: int = int(os.getenv('MAX_RECOMMENDATIONS', '10'))
    min_compatibility_score: float = float(os.getenv('MIN_COMPATIBILITY_SCORE', '50.0'))

    # Caching
    cache_ttl_seconds: int = int(os.getenv('CACHE_TTL_SECONDS', '3600'))
    enable_caching: bool = os.getenv('ENABLE_CACHING', 'True').lower() == 'true'

    # Performance
    recommendation_timeout_seconds: int = int(os.getenv('RECOMMENDATION_TIMEOUT', '5'))


@dataclass
class MonitoringConfig:
    """Monitoring and logging configuration"""
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    enable_metrics: bool = os.getenv('ENABLE_METRICS', 'True').lower() == 'true'
    metrics_port: int = int(os.getenv('METRICS_PORT', '9090'))

    # Sentry (Error Tracking)
    sentry_dsn: Optional[str] = os.getenv('SENTRY_DSN')
    sentry_environment: str = os.getenv('SENTRY_ENVIRONMENT', 'development')
    sentry_traces_sample_rate: float = float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1'))


@dataclass
class SecurityConfig:
    """Security configuration"""
    jwt_secret: str = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
    jwt_algorithm: str = os.getenv('JWT_ALGORITHM', 'HS256')
    jwt_expiration_hours: int = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))

    # API Rate Limiting
    rate_limit_enabled: bool = os.getenv('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
    rate_limit_requests: int = int(os.getenv('RATE_LIMIT_REQUESTS', '100'))
    rate_limit_window_seconds: int = int(os.getenv('RATE_LIMIT_WINDOW', '3600'))

    # CORS
    cors_origins: list = os.getenv('CORS_ORIGINS', '*').split(',')


class Config:
    """Main configuration class"""

    def __init__(self):
        self.server = ServerConfig()
        self.database = DatabaseConfig()
        self.recommendation = RecommendationConfig()
        self.monitoring = MonitoringConfig()
        self.security = SecurityConfig()

    def is_production(self) -> bool:
        """Check if running in production"""
        return self.server.environment.lower() == 'production'

    def is_development(self) -> bool:
        """Check if running in development"""
        return self.server.environment.lower() == 'development'

    def validate(self) -> list:
        """Validate configuration and return list of errors"""
        errors = []

        # Check required fields in production
        if self.is_production():
            if self.security.jwt_secret == 'your-secret-key-change-in-production':
                errors.append("JWT_SECRET must be set in production")

            if not self.database.postgres_password:
                errors.append("POSTGRES_PASSWORD must be set in production")

            if not self.monitoring.sentry_dsn:
                errors.append("SENTRY_DSN should be set in production")

        # Validate weights sum to 1.0
        total_weight = (
                self.recommendation.financial_weight +
                self.recommendation.location_weight +
                self.recommendation.lifestyle_weight
        )
        if abs(total_weight - 1.0) > 0.01:
            errors.append(f"Recommendation weights must sum to 1.0, got {total_weight}")

        return errors

    def __repr__(self) -> str:
        """String representation (safe for logging)"""
        return f"""
OLISTAY Configuration
=====================
Environment: {self.server.environment}
Server: {self.server.host}:{self.server.port}
gRPC Port: {self.server.grpc_port}
Database: {self.database.postgres_host}:{self.database.postgres_port}
Cache: {self.database.redis_host}:{self.database.redis_port}
Debug Mode: {self.server.debug}
Metrics: {'Enabled' if self.monitoring.enable_metrics else 'Disabled'}
        """


# Global configuration instance
config = Config()

if __name__ == '__main__':
    # Validate and display configuration
    print(config)

    errors = config.validate()
    if errors:
        print("\n⚠️  Configuration Errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n✅ Configuration valid")