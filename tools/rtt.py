"""The round trip from this machine to the server: what one request of the final costs a quote.

    python -m tools.rtt        # set SPREAD_URL and SPREAD_KEY first
"""
import time

from spread.client import Client, SpreadError

client, took = Client(), []
for _ in range(21):
    started = time.perf_counter()
    try:
        client.final()
    except SpreadError as error:
        if error.status != 404:  # no final is set: still an answer
            raise
    took.append((time.perf_counter() - started) * 1000)
print(f"first request, with the handshake: {took[0]:.0f} ms; then median {sorted(took[1:])[10]:.0f} ms, fastest {min(took[1:]):.0f}, slowest {max(took[1:]):.0f}")
