from risk_manager.integrations.base import IntegrationProvider, MerchantConnection, DeduplicationCache
from risk_manager.integrations.registry import registry
from risk_manager.integrations.generic_api.adapter import GenericAPIProvider, validate_api_url
from risk_manager.integrations.shopify.adapter import ShopifyProvider
from risk_manager.integrations.razorpay.adapter import RazorpayProvider

# Register default provider implementations
registry.register(GenericAPIProvider())
registry.register(ShopifyProvider())
registry.register(RazorpayProvider())

__all__ = [
    "IntegrationProvider",
    "MerchantConnection",
    "DeduplicationCache",
    "registry",
    "GenericAPIProvider",
    "ShopifyProvider",
    "RazorpayProvider",
    "validate_api_url",
]
