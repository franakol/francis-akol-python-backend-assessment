"""Payment gateway integration (Stripe mock)."""

import secrets
from decimal import Decimal
from typing import Dict

from app.core.config import settings


class PaymentGateway:
    """
    Payment gateway integration.

    This is a mock implementation for Stripe-like payment processing.
    In production, use actual Stripe SDK: stripe.PaymentIntent.create()
    """

    def __init__(self):
        """Initialize payment gateway with API keys."""
        self.secret_key = settings.STRIPE_SECRET_KEY
        self.publishable_key = settings.STRIPE_PUBLISHABLE_KEY

    async def create_payment_intent(
        self, amount: Decimal, currency: str, metadata: Dict = None
    ) -> Dict:
        """
        Create a payment intent.

        Mock implementation - generates fake payment intent ID and client secret.
        In production: stripe.PaymentIntent.create(amount=..., currency=...)

        Args:
            amount: Payment amount in smallest currency unit (cents for USD)
            currency: Currency code (e.g., "USD")
            metadata: Additional metadata

        Returns:
            Payment intent data with id and client_secret
        """
        # Generate mock payment intent ID (like Stripe format)
        intent_id = f"pi_{secrets.token_hex(12)}"
        client_secret = f"{intent_id}_secret_{secrets.token_hex(16)}"

        return {
            "id": intent_id,
            "amount": int(amount * 100),  # Convert to cents
            "currency": currency.lower(),
            "status": "requires_confirmation",
            "client_secret": client_secret,
            "metadata": metadata or {},
        }

    async def confirm_payment_intent(self, intent_id: str) -> Dict:
        """
        Confirm a payment intent.

        Mock implementation - simulates payment confirmation.
        In production: stripe.PaymentIntent.confirm(intent_id)

        Args:
            intent_id: Payment intent ID

        Returns:
            Confirmed payment intent data
        """
        # Generate mock transaction ID
        transaction_id = f"txn_{secrets.token_hex(12)}"

        # Simulate 90% success rate
        import random

        success = random.random() > 0.1

        if success:
            return {
                "id": intent_id,
                "status": "succeeded",
                "transaction_id": transaction_id,
                "charges": {
                    "data": [{"id": transaction_id, "status": "succeeded"}]
                },
            }
        else:
            return {
                "id": intent_id,
                "status": "failed",
                "failure_message": "Card declined - insufficient funds",
            }

    async def refund_payment(
        self, transaction_id: str, reason: str = None
    ) -> Dict:
        """
        Refund a payment.

        Mock implementation - simulates refund processing.
        In production: stripe.Refund.create(charge=transaction_id)

        Args:
            transaction_id: Transaction ID to refund
            reason: Refund reason

        Returns:
            Refund data
        """
        refund_id = f"re_{secrets.token_hex(12)}"

        return {
            "id": refund_id,
            "transaction_id": transaction_id,
            "status": "succeeded",
            "reason": reason,
        }

    async def retrieve_payment_intent(self, intent_id: str) -> Dict:
        """
        Retrieve payment intent details.

        Mock implementation.
        In production: stripe.PaymentIntent.retrieve(intent_id)

        Args:
            intent_id: Payment intent ID

        Returns:
            Payment intent data
        """
        return {
            "id": intent_id,
            "status": "requires_confirmation",
        }


# Global payment gateway instance
payment_gateway = PaymentGateway()
