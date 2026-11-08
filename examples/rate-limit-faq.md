# Rate Limiting FAQ

## What happens when I hit my limit?

The API returns status 429 with a `Retry-After` header. Wait that many seconds before sending the next request.

## Can I get a higher limit?

Yes. Enterprise plans include 1,000 requests per second. Contact your account manager to raise it further.

## Do failed requests count?

- Requests rejected with 429 do not count.
- Requests that fail with a server error do count.
