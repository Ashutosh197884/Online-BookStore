# TODO: Implement Stripe Payment Integration for Book Store App

## Steps to Complete

- [x] Update models.py: Add payment_method, payment_id, and payment_status fields to Order model. (Already done)
- [x] Update requirements.txt: Add stripe dependency.
- [x] Update app.py: Add Stripe configuration, modify checkout route to create Stripe Checkout session, add routes for payment success and cancellation.
- [x] Update templates/cart.html: Replace direct checkout with "Proceed to Payment" button and payment method selection.
- [x] Install dependencies using pip install -r requirements.txt.
- [ ] Test payment flow locally (requires Stripe test keys).
- [x] Ensure secure handling of API keys (use environment variables).
- [x] Update admin dashboard to reflect paid orders (if needed - no changes required).
