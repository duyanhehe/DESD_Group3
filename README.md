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
   - Pull the model: `ollama pull qwen2.5:7b-instruct`

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
        ollama pull qwen2.5:7b-instruct
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

# Testing with pytest

This project uses **pytest** for unit and integration testing with support for Django models, views, and API endpoints.

## Running Tests

Run all tests:
```bash
uv run pytest
```

Run tests in a specific app:
```bash
uv run pytest apps/products/
```

Run a specific test file:
```bash
uv run pytest apps/accounts/tests.py
```

Run a specific test:
```bash
uv run pytest apps/accounts/tests.py::TestUserModel::test_create_user
```

Run tests matching a pattern:
```bash
uv run pytest -k "payment" -v
```

## Test Coverage

The current automated suite is aligned with `Test-Cases.pdf`. The app-level `tests.py` files cover the documented stakeholder test cases from **TC-001** through **TC-025**, with non-PDF implementation-only tests removed.

Current suite summary:

| Area | Covered PDF test cases |
|------|------------------------|
| Accounts | TC-001, TC-002, TC-022 |
| Products, Categories, Allergens | TC-003, TC-004, TC-005, TC-011, TC-014, TC-015, TC-016, TC-019, TC-020, TC-023, TC-024 |
| Orders and Cart | TC-006, TC-007, TC-008, TC-009, TC-010, TC-017, TC-018, TC-021 |
| Logistics | TC-013 |
| Payments and Settlements | TC-007, TC-008, TC-012, TC-025 |

Run the PDF-mapped app test suite:
```bash
uv run pytest apps
```

Latest verified result:
```text
28 passed
```

Generate the HTML coverage report:
```bash
uv run pytest --cov=apps --cov-report=html
```

View the report:
```
htmlcov/index.html
```

Coverage output is useful for identifying untested code paths, but the primary acceptance target for this project is matching the user-facing test cases in `Test-Cases.pdf`.

## Writing Tests

### Basic Test Structure

Tests are typically organized in a `tests.py` file in each app:

```python
import pytest
from django.contrib.auth import get_user_model
from apps.products.models import Product

User = get_user_model()

@pytest.mark.django_db
class TestProductModel:
    def test_create_product(self):
        product = Product.objects.create(
            name="Organic Apple",
            price=5.99,
            description="Fresh organic apple"
        )
        assert product.name == "Organic Apple"
        assert Product.objects.count() == 1
```

### Using Fixtures

Define reusable fixtures in `conftest.py`:

```python
@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123"
    )

@pytest.fixture
def authenticated_client(client, user):
    client.force_login(user)
    return client
```

Use fixtures in tests:
```python
@pytest.mark.django_db
def test_product_view(authenticated_client):
    response = authenticated_client.get('/products/')
    assert response.status_code == 200
```

### Testing Views & API

Test API endpoints:
```python
@pytest.mark.django_db
def test_product_api_list(authenticated_client, product):
    response = authenticated_client.get('/api/products/')
    assert response.status_code == 200
    assert len(response.json()) > 0
```

Test with different user types:
```python
@pytest.fixture
def producer(db):
    user = User.objects.create_user(username="producer")
    user.user_type = "PRODUCER"
    user.save()
    return user

@pytest.mark.django_db
def test_only_producer_can_create(authenticated_client, producer):
    client = authenticated_client
    client.force_login(producer)
    response = client.post('/api/products/', {"name": "Test"})
    assert response.status_code == 201
```

## pytest Configuration

Configuration is defined in `pytest.ini`:
- Database transactions are rolled back after each test
- Django settings module is configured
- Markers are defined for organization

Common pytest flags:
```bash
pytest -v                    # Verbose output
pytest -s                    # Show print statements
pytest --lf                  # Run last failed tests
pytest --ff                  # Run failed tests first
pytest -x                    # Stop on first failure
pytest --tb=short            # Shorter traceback format
pytest -k "test_" --collect-only  # List tests without running
```

## Best Practices

1. **Use `@pytest.mark.django_db`** for tests that access the database
2. **Keep tests independent** - don't rely on execution order
3. **Use fixtures** for common setup (users, products, etc.)
4. **Mock external services** (Stripe, Ollama) to avoid real API calls
5. **Test edge cases** - empty results, invalid inputs, permissions
6. **Use descriptive test names** - `test_create_product_with_valid_data` not `test1`
7. **Separate unit and integration tests** using markers:
   ```python
   @pytest.mark.unit
   def test_model_logic():
       pass
   
   @pytest.mark.integration
   def test_api_workflow():
       pass
   ```

---

