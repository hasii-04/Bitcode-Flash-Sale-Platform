import asyncio
import httpx
import time
import statistics

API_URL = "http://localhost:8080/api/v1"
EMAIL = "maya@swiftdrop.test"
PASSWORD = "password123"

async def run_load_test(event_id, item_id, num_requests):
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login
        login_res = await client.post(f"{API_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
        if login_res.status_code != 200:
            print(f"Login failed! {login_res.status_code} {login_res.text}")
            return
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        print(f"Starting load test: {num_requests} concurrent requests for Item ID {item_id}...")
        
        start_time = time.perf_counter()
        tasks = [client.post(f"{API_URL}/purchases", json={"event_id": event_id, "item_id": item_id}, headers=headers) for _ in range(num_requests)]
        
        responses = await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        
        durations = [r.elapsed.total_seconds() * 1000 for r in responses]
        status_codes = [r.status_code for r in responses]
        
        success = status_codes.count(200)
        failed = status_codes.count(400)
        errors = len(status_codes) - success - failed
        
        print("\n--- Load Test Results ---")
        print(f"Total Requests: {num_requests}")
        print(f"Successful Reservations (200 OK): {success}")
        print(f"Sold Out / Rejected (400 Bad Request): {failed}")
        print(f"Errors (500/Other): {errors}")
        print(f"Total Duration: {end_time - start_time:.2f} seconds")
        print(f"Average Latency: {statistics.mean(durations):.2f} ms")
        if len(durations) > 1:
            print(f"P95 Latency: {statistics.quantiles(durations, n=20)[18]:.2f} ms")
        print("-------------------------\n")

if __name__ == "__main__":
    asyncio.run(run_load_test(event_id=2, item_id=3, num_requests=200))
