# Food Network Marketplace (Django)

A multi-vendor food marketplace built with **Django (full-stack with HTML templates)**, based on BPMN workflows including ordering, payments, logistics, and settlement.

---

# Features

*  Customer & Producer
*  Product browsing and cart system
*  Order processing
*  Payment
*  Logistics tracking
*  Settlement system

---

#  Project Architecture

```
food_network/
│
├── core/                 # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── apps/                 # Django applications
│   ├── accounts/         # User authentication (customer, producer)
│   ├── products/         # Product listings & management
│   ├── orders/           # Cart & order processing
│   ├── payments/         # Payment processing & settlements
│   ├── logistics/        # Delivery & shipping tracking
│   ├── ai_engine/        # AI features (chatbot, grading, recommendations)
│   ├── allergens/        # Allergen management
│   └── categories/       # Product categories
│
├── templates/            # HTML templates
│   ├── accounts/
│   ├── orders/
│   ├── payments/
│   └── products/
│
├── static/               # CSS, JavaScript
├── media/                # Uploaded images
│
├── docker-compose.yml    # Docker orchestration
├── Dockerfile            # Container definition
├── pyproject.toml        # uv dependency management
└── manage.py
```

---

# Local Setup Guide

---

## Prerequisites

Before starting local setup, ensure you have:

1. **Stripe CLI** (for webhook forwarding):
   - Install from [stripe.com/docs/stripe-cli](https://stripe.com/docs/stripe-cli)
   - Login: `stripe login`

2. **Ollama** (for AI chatbot features):
   - Install from [ollama.com](https://ollama.com)
   - Pull the model: `ollama pull qwen2.5:7b`

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

Edit `.env` with your environment variables:

| Variable | Purpose | Source |
|----------|---------|--------|
| `SECRET_KEY` | Django security key | Generate a random string |
| `DEBUG` | Development mode | `True` for local dev |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | PostgreSQL credentials | Your local database |
| `STRIPE_PUBLIC_KEY`, `STRIPE_SECRET_KEY` | Payment processing | [Stripe Dashboard](https://dashboard.stripe.com/apikeys) |
| `STRIPE_WEBHOOK_SECRET` | Webhook verification | `stripe listen` CLI output |
| `KAGGLE_USERNAME`, `KAGGLE_KEY` | Download AI models | [Kaggle Account](https://www.kaggle.com/settings/account) |
| `OLLAMA_API_URL` | AI chatbot endpoint | Default: `http://localhost:11434/api/generate` |


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

In a separate terminal, start Stripe webhook forwarding:

```
stripe listen --forward-to localhost:8000/payments/api/v1/webhook/
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
    -   **Pull the Model**:
        ```bash
        ollama pull qwen2.5:7b
        ```
    -   **Restart Ollama** after applying these changes.
3.  **Environment Keys**: Ensure environment variables are configured in your `.env` file.

## Running with Docker

1.  **Prepare Environment**:
    ```bash
    cp .env.example .env
    # Edit .env to include your Stripe keys and database credentials
    ```

2.  **Build and Start**: \
    Build
    ```bash
    docker-compose up --build
    ```
    Run
    ```bash
    docker-compose up -d
    ```
    This command builds the Django container (Python 3.11), starts the PostgreSQL database, and automatically runs all migrations.

3.  **Accessing the Services**:
    - **Marketplace**: [http://localhost:8000](http://localhost:8000)
    - **Admin Panel**: [http://localhost:8000/admin](http://localhost:8000/admin)
    - **Stripe Webhooks**: The `stripe` container automatically forwards events to the app. Check the logs to get your signing secret:
      ```bash
      docker logs brfn_stripe
      ```

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

