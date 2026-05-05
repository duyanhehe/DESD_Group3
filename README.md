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

# Docker Usage

You can run the entire application, including the database, using Docker Compose.

## Prerequisites

1.  **Docker & Docker Compose** installed on your system.
2.  **Local Ollama** (required for the AI Chatbot):
    -   Ensure Ollama is running on your host machine.
    -   Configure it to allow connections from Docker containers:
        ```powershell
        # Run in PowerShell as Administrator
        [System.Environment]::SetEnvironmentVariable('OLLAMA_HOST', '0.0.0.0', 'User')
        [System.Environment]::SetEnvironmentVariable('OLLAMA_ORIGINS', '*', 'User')
        ```
    -   **Restart Ollama** after applying these changes.
3.  **Stripe Keys**: Ensure `STRIPE_PUBLIC_KEY` and `STRIPE_SECRET_KEY` are configured in your `.env` file.

## Running with Docker

1.  **Prepare Environment**:
    ```bash
    cp .env.example .env
    # Edit .env to include your Stripe keys and database credentials
    ```

2.  **Build and Start**:
    ```bash
    docker-compose up --build
    ```
    This command builds the Django container (Python 3.11), starts the PostgreSQL database, and automatically runs all migrations.

3.  **Accessing the Services**:
    - **Marketplace**: [http://localhost:8000](http://localhost:8000)
    - **Admin Panel**: [http://localhost:8000/admin](http://localhost:8000/admin)

4.  **Useful Commands**:
    - **Create Superuser**:
      ```bash
      docker exec -it brfn_app python manage.py createsuperuser
      ```
    - **Stop Services**:
      ```bash
      docker-compose down
      ```

# Admin & Treasury Management

To access the administrative back-end and the Treasury (Settlement) system, follow these steps.

## 1. Create a Superuser
You must first create a main administrator account to log in to the admin panel.

**With Docker:**
```bash
docker exec -it brfn_app python manage.py createsuperuser
```

**Locally:**
```bash
uv run python manage.py createsuperuser
```

## 2. Promote Users to Staff (Treasury Access)
Regular users (like Producers or Customers) cannot access the Treasury dashboard by default. To promote a user so they can manage settlements:

1.  Log in to the **Admin Panel**: [http://localhost:8000/admin](http://localhost:8000/admin) using your Superuser account.
2.  Navigate to **Users** (under the Accounts section).
3.  Click on the **Username** of the account you wish to promote.
4.  Scroll down to the **Permissions** section.
5.  Check the box for **Staff status** (Designates whether the user can log into this admin site).
6.  Click **Save** at the bottom of the page.
7.  This user can now access the **Treasury** link in the main site navigation to manage settlements and payouts.

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

