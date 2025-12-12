"""
Minimal payment service for deployment
Provides basic payment functionality without external dependencies
"""

class GCashService:
    """Minimal GCash service for deployment"""
    
    def __init__(self):
        self.enabled = False
        
    def create_payment(self, amount, description="Payment"):
        """Create a simulated payment"""
        return {
            'success': False,
            'message': 'Payment service not configured for deployment',
            'payment_id': None,
            'checkout_url': None
        }
    
    def verify_payment(self, payment_id):
        """Verify a payment"""
        return {
            'success': False,
            'status': 'pending',
            'message': 'Payment verification not available'
        }

# Create service instance
gcash_service = GCashService()

def simulate_payment_success(amount, description="Test Payment"):
    """Simulate a successful payment for testing"""
    return {
        'success': True,
        'payment_id': f'sim_{int(amount)}_{hash(description) % 10000}',
        'status': 'paid',
        'amount': amount,
        'description': description,
        'message': 'Simulated payment successful'
    }

def simulate_payment_failure(amount, description="Test Payment"):
    """Simulate a failed payment for testing"""
    return {
        'success': False,
        'payment_id': None,
        'status': 'failed',
        'amount': amount,
        'description': description,
        'message': 'Simulated payment failed'
    }