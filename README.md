# Food Network Marketplace (Django)

A multi-vendor food marketplace built with **Django (full-stack with HTML templates)**, based on BPMN workflows including ordering, payments, logistics, and settlement.

---

# Features

*  Customer & Producer roles
*  Product browsing and cart system
*  Order processing
*  Payment simulation
*  Logistics tracking (basic)
*  Settlement system (planned)

---

#  Project Architecture

```
food_network/
│
├── core/              # Django project settings
│
├── accounts/          # User model (customer, producer)
├── products/          # Product listings (by producers)
├── orders/            # Cart + order management
├── payments/          # Payment processing logic
├── logistics/         # Delivery & shipping
│
├── templates/         # HTML templates
├── static/            # CSS, JS
├── media/             # Uploaded images
│
├── .env               # Environment variables
├── pyproject.toml     # uv dependency management
└── manage.py
```

---

# Setup Guide

---

## 1. Install uv

```
pip install uv
```

---

## 2. Create Virtual Environment

```
uv venv
```

Activate:

**Windows**

```
.venv\Scripts\activate
```

**Mac/Linux**

```
source .venv/bin/activate
```

---

## 4. Install Dependencies

```
uv sync
```


---

## 5. Setup Environment Variables

```
cp .env.example .env
```

Edit `.env`:


---

## 6. Run Migrations

```
uv run python manage.py makemigrations
uv run python manage.py migrate
```

---

## 7. Create Superuser

```
uv run python manage.py createsuperuser
```

---

## 8. Run Development Server

```
uv run python manage.py runserver
```

Visit:

```
http://127.0.0.1:8000/
```

Admin:

```
http://127.0.0.1:8000/admin/
```

---

# Development Workflow

| Task              | Command                                  |
| ----------------  | ---------------------------------------- |
| Run server        | `uv run python manage.py runserver`      |
| Migrations        | `uv run python manage.py makemigrations` |
| Apply migrations  | `uv run python manage.py migrate`        |
| Install package   | `uv add <package>`                       |
| Add app           | `uv run python manage.py startapp <app>` |
| Load data into db | `uv run python manage.py loaddata <app>` |

---
#  Notes

* Do NOT commit `.env`
* Always use `uv` instead of `pip`
* Custom user model must be set before migrations

---

# System Flow 

### Customer Flow

1. Browse products
2. Add to cart
3. Checkout
4. Make payment

### Marketplace Flow

1. Receive order
2. Aggregate items
3. Process payment
4. Coordinate delivery
5. Complete transaction

### Producer Flow

1. Manage product listings
2. Receive orders
3. Fulfill items
4. Get paid (settlement phase)



---

