"""A dependency-free job for learning bundle deployment and CI/CD promotion."""

import argparse
import json


def summarize_orders(orders):
    """Sum paid orders in integer cents; reject malformed inputs."""
    seen = set()
    paid_count = 0
    total_cents = 0
    for order in orders:
        order_id = order["id"]
        if order_id in seen:
            raise ValueError(f"Duplicate order ID: {order_id}")
        seen.add(order_id)
        amount = order["amount_cents"]
        if type(amount) is not int or amount < 0:
            raise ValueError("Order amounts must be nonnegative integer cents")
        if order["status"] not in {"paid", "cancelled"}:
            raise ValueError("Unsupported order status")
        if order["status"] == "paid":
            paid_count += 1
            total_cents += amount
    return {"paid_orders": paid_count, "total_cents": total_cents}


def run_demo(environment, batch_size, min_total_cents, release_sha="local"):
    if environment not in {"dev", "staging", "prod"}:
        raise ValueError("Environment must be dev, staging, or prod")
    if type(batch_size) is not int or not 1 <= batch_size <= 100000:
        raise ValueError("Batch size must be an integer between 1 and 100000")
    if type(min_total_cents) is not int or min_total_cents < 0:
        raise ValueError("Minimum total must be nonnegative integer cents")

    # Every fifth order is cancelled; every order is worth 250 cents.
    orders = [
        {"id": index, "amount_cents": 250,
         "status": "cancelled" if index % 5 == 0 else "paid"}
        for index in range(1, batch_size + 1)
    ]
    summary = summarize_orders(orders)
    expected_paid = batch_size - batch_size // 5
    if summary != {"paid_orders": expected_paid, "total_cents": expected_paid * 250}:
        raise ValueError("Synthetic fixture check failed")
    if summary["total_cents"] < min_total_cents:
        raise ValueError(
            f"Quality check failed: {summary['total_cents']} < {min_total_cents} cents"
        )
    return {
        "environment": environment,
        "release_sha": release_sha,
        "input_orders": batch_size,
        **summary,
        "quality_check": "passed",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True, choices=["dev", "staging", "prod"])
    parser.add_argument("--batch-size", type=int, required=True)
    parser.add_argument("--min-total-cents", type=int, required=True)
    parser.add_argument("--release-sha", default="local")
    args = parser.parse_args()
    print(json.dumps(run_demo(
        args.environment, args.batch_size, args.min_total_cents, args.release_sha
    ), sort_keys=True))


if __name__ == "__main__":
    main()
