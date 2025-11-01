# SHALINIMB18.github.io

## Payment configuration (Razorpay)

For local development, the project uses Razorpay test keys. You can override the defaults by setting environment variables in your shell or a .env loader:

- RAZORPAY_KEY_ID - your Razorpay key id (default is a test key in settings)
- RAZORPAY_KEY_SECRET - your Razorpay secret (default placeholder in settings)

To enable webhooks in Razorpay dashboard for local testing, use a tunneling tool (like ngrok) and point webhooks to:

http://<your-tunnel>/books/api/payment/webhook/

Remember: never commit real production keys to source control. Use environment variables or a secrets manager in production.

## Testing webhooks locally (ngrok)

To test Razorpay webhooks on your local development server, use a tunneling tool such as ngrok.

1. Install and run ngrok (or similar) to forward HTTP traffic to your local Django server (default port 8000):

	ngrok http 8000

2. Copy the forwarding URL shown by ngrok (e.g. https://abcd1234.ngrok.io) and configure Razorpay webhooks to point to:

	https://<your-ngrok-id>.ngrok.io/books/api/payment/webhook/

3. In Razorpay dashboard, set the webhook secret (optional) and use the same secret in your environment as RAZORPAY_KEY_SECRET.

4. Send test events from the Razorpay dashboard or trigger a payment in the checkout flow; your local server will receive and log the webhook and persist a `PaymentEvent`.

Notes:
- Keep ngrok running while testing webhooks.
- Webhook payloads will be verified using the secret if present; in tests the verification is mocked.
- Use the Django admin to inspect `PaymentEvent` records under the Books app.