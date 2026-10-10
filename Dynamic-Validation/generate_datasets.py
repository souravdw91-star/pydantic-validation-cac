"""
generate_datasets.py - Synthetic Dataset Generator for Scalability Testing

Generates large datasets for:
1. orders.txt (~10,000 records)
2. transactions.txt (~10,000 records)
3. shipments.txt (~10,000 records)

Includes realistic distributions with ~1.5% intentional data quality anomalies
(bad types, length overflows, corrupted booleans) to thoroughly test the
validation pipeline's error detection and scalability.
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "Data" / "input"
INPUT_DIR.mkdir(parents=True, exist_ok=True)

# Seed for reproducibility
random.seed(42)

NUM_RECORDS = 10000

CITIES = ["Bangalore", "Mumbai", "Delhi", "Hyderabad", "Pune", "Chennai", "Kolkata", "Bhubaneswar", "Cuttack", "Jaipur"]
STATUSES = ["PENDING", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"]
PAYMENT_METHODS = ["CREDIT_CARD", "DEBIT_CARD", "UPI", "NET_BANKING", "WALLET", "COD"]
CARRIERS = ["FedEx", "DHL", "BlueDart", "Delhivery", "DTDC", "Ekart"]
CURRENCIES = ["INR", "USD", "EUR", "GBP", "SGD"]


def generate_orders(num_rows: int = NUM_RECORDS) -> None:
    file_path = INPUT_DIR / "orders.txt"
    headers = ["order_id", "customer_id", "order_status", "order_amount", "order_date", "shipping_city"]
    
    start_date = datetime(2025, 1, 1)
    rows = []
    
    print(f"Generating {num_rows} records for orders.txt...")
    for i in range(1, num_rows + 1):
        order_date = (start_date + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d")
        
        # Inject intentional errors in ~1.5% of rows
        error_type = random.randint(1, 100) if (i % 65 == 0) else 0
        
        if error_type == 1:
            # Bad order_id (string instead of int)
            order_id = f"INVALID_{i}"
            cust_id = random.randint(1000, 9999)
            status = random.choice(STATUSES)
            amount = round(random.uniform(10.0, 5000.0), 2)
            city = random.choice(CITIES)
        elif error_type == 2:
            # Bad amount (string instead of float)
            order_id = i
            cust_id = random.randint(1000, 9999)
            status = random.choice(STATUSES)
            amount = "FREE_PROMO"
            city = random.choice(CITIES)
        elif error_type == 3:
            # Overflow length on status (max_length=50)
            order_id = i
            cust_id = random.randint(1000, 9999)
            status = "THIS_ORDER_STATUS_STRING_IS_EXTREMELY_LONG_AND_EXCEEDS_THE_MAXIMUM_ALLOWED_LENGTH_LIMIT_OF_50_CHARACTERS"
            amount = round(random.uniform(10.0, 5000.0), 2)
            city = random.choice(CITIES)
        else:
            # Clean record
            order_id = i
            cust_id = random.randint(1000, 9999)
            status = random.choice(STATUSES)
            amount = round(random.uniform(10.0, 5000.0), 2)
            city = random.choice(CITIES)

        rows.append({
            "order_id": order_id,
            "customer_id": cust_id,
            "order_status": status,
            "order_amount": amount,
            "order_date": order_date,
            "shipping_city": city,
        })

    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"-> Successfully written to {file_path}")


def generate_transactions(num_rows: int = NUM_RECORDS) -> None:
    file_path = INPUT_DIR / "transactions.txt"
    headers = ["txn_id", "order_id", "payment_method", "txn_amount", "is_successful", "currency"]
    
    rows = []
    print(f"Generating {num_rows} records for transactions.txt...")
    for i in range(1, num_rows + 1):
        error_type = random.randint(1, 100) if (i % 70 == 0) else 0
        
        if error_type == 1:
            # Bad boolean (not parseable as bool)
            txn_id = 50000 + i
            order_id = random.randint(1, num_rows)
            method = random.choice(PAYMENT_METHODS)
            amount = round(random.uniform(10.0, 5000.0), 2)
            is_success = "MAYBE_FAILED"
            currency = random.choice(CURRENCIES)
        elif error_type == 2:
            # Currency exceeds max_length of 10
            txn_id = 50000 + i
            order_id = random.randint(1, num_rows)
            method = random.choice(PAYMENT_METHODS)
            amount = round(random.uniform(10.0, 5000.0), 2)
            is_success = "true"
            currency = "INTERNATIONAL_UNITED_STATES_DOLLAR"
        elif error_type == 3:
            # Bad txn_id
            txn_id = "TXN_PENDING"
            order_id = random.randint(1, num_rows)
            method = random.choice(PAYMENT_METHODS)
            amount = round(random.uniform(10.0, 5000.0), 2)
            is_success = "true"
            currency = random.choice(CURRENCIES)
        else:
            txn_id = 50000 + i
            order_id = random.randint(1, num_rows)
            method = random.choice(PAYMENT_METHODS)
            amount = round(random.uniform(10.0, 5000.0), 2)
            is_success = random.choice(["true", "false", "1", "0"])
            currency = random.choice(CURRENCIES)

        rows.append({
            "txn_id": txn_id,
            "order_id": order_id,
            "payment_method": method,
            "txn_amount": amount,
            "is_successful": is_success,
            "currency": currency,
        })

    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"-> Successfully written to {file_path}")


def generate_shipments(num_rows: int = NUM_RECORDS) -> None:
    file_path = INPUT_DIR / "shipments.txt"
    headers = ["shipment_id", "order_id", "carrier", "tracking_number", "weight_kg", "delivery_days"]
    
    rows = []
    print(f"Generating {num_rows} records for shipments.txt...")
    for i in range(1, num_rows + 1):
        error_type = random.randint(1, 100) if (i % 75 == 0) else 0
        
        if error_type == 1:
            # Bad weight (string instead of float)
            shipment_id = 90000 + i
            order_id = random.randint(1, num_rows)
            carrier = random.choice(CARRIERS)
            tracking = f"TRK{random.randint(10000000, 99999999)}"
            weight = "VERY_HEAVY"
            delivery_days = random.randint(1, 10)
        elif error_type == 2:
            # Bad delivery days (string instead of int)
            shipment_id = 90000 + i
            order_id = random.randint(1, num_rows)
            carrier = random.choice(CARRIERS)
            tracking = f"TRK{random.randint(10000000, 99999999)}"
            weight = round(random.uniform(0.1, 50.0), 2)
            delivery_days = "OVERNIGHT"
        elif error_type == 3:
            # Carrier exceeding length 50
            shipment_id = 90000 + i
            order_id = random.randint(1, num_rows)
            carrier = "GLOBAL_EXPRESS_LOGISTICS_AND_FREIGHT_FORWARDING_SERVICES_LIMITED_COMPANY"
            tracking = f"TRK{random.randint(10000000, 99999999)}"
            weight = round(random.uniform(0.1, 50.0), 2)
            delivery_days = random.randint(1, 10)
        else:
            shipment_id = 90000 + i
            order_id = random.randint(1, num_rows)
            carrier = random.choice(CARRIERS)
            tracking = f"TRK{random.randint(10000000, 99999999)}"
            weight = round(random.uniform(0.1, 50.0), 2)
            delivery_days = random.randint(1, 10)

        rows.append({
            "shipment_id": shipment_id,
            "order_id": order_id,
            "carrier": carrier,
            "tracking_number": tracking,
            "weight_kg": weight,
            "delivery_days": delivery_days,
        })

    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"-> Successfully written to {file_path}")


if __name__ == "__main__":
    generate_orders()
    generate_transactions()
    generate_shipments()
    print("All datasets generated successfully!")
