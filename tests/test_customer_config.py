"""Tests for customer configuration endpoints."""

import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.utils.customer_config import CustomerConfigManager

client = TestClient(app)


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file for testing."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "customers.json"
    
    # Create initial config with test data
    initial_data = {
        "customers": [
            {
                "customer_id": "test-company",
                "customer_name": "Test Company",
                "director": "John Doe",
                "bizdev": ["Alice"],
                "career_links": [
                    {"label": "Main Portal", "url": "https://example.com/careers"}
                ]
            }
        ]
    }
    
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(initial_data, f, indent=2)
    
    return config_file


class TestCustomerConfigManager:
    """Test CustomerConfigManager utility class."""
    
    def test_read_config_success(self, temp_config_file):
        """Test reading valid config file."""
        manager = CustomerConfigManager(temp_config_file)
        customers = manager.read_config()
        
        assert len(customers) == 1
        assert customers[0]["customer_id"] == "test-company"
        assert customers[0]["customer_name"] == "Test Company"
    
    def test_read_config_file_not_found(self, tmp_path):
        """Test reading non-existent config file."""
        manager = CustomerConfigManager(tmp_path / "nonexistent.json")
        
        with pytest.raises(FileNotFoundError):
            manager.read_config()
    
    def test_read_config_invalid_json(self, tmp_path):
        """Test reading malformed JSON config file."""
        config_file = tmp_path / "invalid.json"
        with open(config_file, "w") as f:
            f.write("{invalid json")
        
        manager = CustomerConfigManager(config_file)
        
        with pytest.raises(json.JSONDecodeError):
            manager.read_config()
    
    def test_generate_customer_id(self, temp_config_file):
        """Test customer ID slug generation."""
        manager = CustomerConfigManager(temp_config_file)
        
        assert manager._generate_customer_id("Cisco Systems") == "cisco-systems"
        assert manager._generate_customer_id("Dell Technologies") == "dell-technologies"
        assert manager._generate_customer_id("HPE Inc.") == "hpe-inc"
        assert manager._generate_customer_id("  Broadcom  ") == "broadcom"
    
    def test_add_customer_success(self, temp_config_file):
        """Test successfully adding a new customer."""
        manager = CustomerConfigManager(temp_config_file)
        
        new_customer = manager.add_customer(
            customer_name="New Company",
            director="Jane Smith",
            bizdev=["Bob", "Carol"],
            career_links=[
                {"label": "Portal 1", "url": "https://new.com/jobs"},
                {"label": "Portal 2", "url": "https://new.com/careers"}
            ]
        )
        
        # Verify returned customer object
        assert new_customer["customer_id"] == "new-company"
        assert new_customer["customer_name"] == "New Company"
        assert new_customer["director"] == "Jane Smith"
        assert len(new_customer["bizdev"]) == 2
        assert len(new_customer["career_links"]) == 2
        
        # Verify it was written to file
        customers = manager.read_config()
        assert len(customers) == 2
        assert customers[1]["customer_id"] == "new-company"
    
    def test_add_customer_duplicate_id(self, temp_config_file):
        """Test adding customer with duplicate customer_id."""
        manager = CustomerConfigManager(temp_config_file)
        
        # Try to add a customer with same name (will generate same ID)
        with pytest.raises(ValueError) as exc_info:
            manager.add_customer(
                customer_name="Test Company",  # Same as existing
                director="Jane",
                bizdev=["Alice"],
                career_links=[{"label": "Test", "url": "https://test.com"}]
            )
        
        assert "already exists" in str(exc_info.value).lower()
    
    def test_add_customer_atomic_write(self, temp_config_file):
        """Test atomic write doesn't corrupt on failure."""
        manager = CustomerConfigManager(temp_config_file)
        
        # Read initial state
        initial_customers = manager.read_config()
        initial_count = len(initial_customers)
        
        # Successfully add a customer
        manager.add_customer(
            customer_name="Valid Company",
            director="Director",
            bizdev=["BD"],
            career_links=[{"label": "Link", "url": "https://valid.com"}]
        )
        
        # Verify file has 2 customers now
        customers = manager.read_config()
        assert len(customers) == initial_count + 1
        
        # Verify no temp file left behind
        temp_file = temp_config_file.with_suffix('.json.tmp')
        assert not temp_file.exists()
    
    def test_validate_customer_unique(self, temp_config_file):
        """Test customer ID uniqueness validation."""
        manager = CustomerConfigManager(temp_config_file)
        existing = manager.read_config()
        
        # Should not raise for unique ID
        manager._validate_customer_unique("unique-id", existing)
        
        # Should raise for duplicate ID
        with pytest.raises(ValueError) as exc_info:
            manager._validate_customer_unique("test-company", existing)
        
        assert "already exists" in str(exc_info.value).lower()
    
    def test_update_customer_success(self, temp_config_file):
        """Test successfully updating a customer."""
        manager = CustomerConfigManager(temp_config_file)
        
        # Update the existing test customer
        updated_customer = manager.update_customer(
            customer_id="test-company",
            customer_name="Updated Company",
            director="New Director",
            bizdev=["Alice", "Bob"],
            career_links=[
                {"label": "New Portal", "url": "https://updated.com/careers"}
            ]
        )
        
        # Verify returned customer object
        assert updated_customer["customer_id"] == "updated-company"  # ID changed due to name change
        assert updated_customer["customer_name"] == "Updated Company"
        assert updated_customer["director"] == "New Director"
        assert len(updated_customer["bizdev"]) == 2
        assert updated_customer["bizdev"] == ["Alice", "Bob"]
        assert len(updated_customer["career_links"]) == 1
        
        # Verify it was written to file
        customers = manager.read_config()
        assert len(customers) == 1
        assert customers[0]["customer_id"] == "updated-company"
    
    def test_update_customer_partial(self, temp_config_file):
        """Test updating only some fields of a customer."""
        manager = CustomerConfigManager(temp_config_file)
        
        # Update only the director
        updated_customer = manager.update_customer(
            customer_id="test-company",
            director="Different Director"
        )
        
        # Verify only director changed
        assert updated_customer["customer_id"] == "test-company"  # ID unchanged
        assert updated_customer["customer_name"] == "Test Company"  # Name unchanged
        assert updated_customer["director"] == "Different Director"  # Director changed
        assert updated_customer["bizdev"] == ["Alice"]  # Bizdev unchanged
    
    def test_update_customer_not_found(self, temp_config_file):
        """Test updating non-existent customer."""
        manager = CustomerConfigManager(temp_config_file)
        
        with pytest.raises(ValueError) as exc_info:
            manager.update_customer(
                customer_id="non-existent",
                director="Someone"
            )
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_update_customer_name_conflict(self, temp_config_file):
        """Test updating customer name to one that already exists."""
        manager = CustomerConfigManager(temp_config_file)
        
        # Add a second customer
        manager.add_customer(
            customer_name="Second Company",
            director="Director",
            bizdev=["Contact"],
            career_links=[{"label": "Link", "url": "https://second.com"}]
        )
        
        # Try to update test-company to have same name as second-company
        with pytest.raises(ValueError) as exc_info:
            manager.update_customer(
                customer_id="test-company",
                customer_name="Second Company"  # This would generate "second-company" ID
            )
        
        assert "already exists" in str(exc_info.value).lower()


class TestCustomerEndpoints:
    """Test customer API endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup_test_config(self, temp_config_file, monkeypatch):
        """Set up test config for each endpoint test."""
        # Monkey-patch the config path in CustomerConfigManager
        original_init = CustomerConfigManager.__init__
        
        def patched_init(self, config_path=None):
            original_init(self, config_path or temp_config_file)
        
        monkeypatch.setattr(CustomerConfigManager, "__init__", patched_init)
    
    def test_get_customers_success(self):
        """Test GET /customers endpoint returns customers."""
        response = client.get("/customers")
        
        assert response.status_code == 200
        data = response.json()
        assert "customers" in data
        assert len(data["customers"]) >= 1
        assert data["customers"][0]["customer_id"] == "test-company"
    
    def test_post_customer_success(self):
        """Test POST /customers endpoint adds new customer."""
        new_customer_data = {
            "customer_name": "Another Company",
            "director": "Director Name",
            "bizdev": ["Contact1", "Contact2"],
            "career_links": [
                {"label": "Career Portal", "url": "https://another.com/jobs"}
            ]
        }
        
        response = client.post("/customers", json=new_customer_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Customer added successfully"
        assert data["customer"]["customer_id"] == "another-company"
        assert data["customer"]["customer_name"] == "Another Company"
    
    def test_post_customer_duplicate_name(self):
        """Test POST /customers rejects duplicate customer name."""
        duplicate_data = {
            "customer_name": "Test Company",  # Same as existing
            "director": "Someone",
            "bizdev": ["Person"],
            "career_links": [
                {"label": "Link", "url": "https://test.com/jobs"}
            ]
        }
        
        response = client.post("/customers", json=duplicate_data)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()
    
    def test_post_customer_invalid_url(self):
        """Test POST /customers rejects malformed URL."""
        invalid_data = {
            "customer_name": "Invalid URL Company",
            "director": "Director",
            "bizdev": ["Contact"],
            "career_links": [
                {"label": "Bad Link", "url": "not-a-valid-url"}
            ]
        }
        
        response = client.post("/customers", json=invalid_data)
        
        assert response.status_code == 422  # Pydantic validation error
    
    def test_post_customer_empty_career_links(self):
        """Test POST /customers rejects empty career_links."""
        invalid_data = {
            "customer_name": "No Links Company",
            "director": "Director",
            "bizdev": ["Contact"],
            "career_links": []
        }
        
        response = client.post("/customers", json=invalid_data)
        
        assert response.status_code == 422  # Pydantic validation error
    
    def test_post_customer_empty_name(self):
        """Test POST /customers rejects empty customer_name."""
        invalid_data = {
            "customer_name": "   ",  # Just whitespace
            "director": "Director",
            "bizdev": ["Contact"],
            "career_links": [
                {"label": "Link", "url": "https://test.com"}
            ]
        }
        
        response = client.post("/customers", json=invalid_data)
        
        assert response.status_code == 422  # Pydantic validation error
    
    def test_put_customer_success(self):
        """Test PUT /customers/{id} endpoint updates customer."""
        update_data = {
            "customer_name": "Updated Test Company",
            "director": "New Director",
            "bizdev": ["Alice", "Bob"],
            "career_links": [
                {"label": "Updated Portal", "url": "https://updated.com/jobs"}
            ]
        }
        
        response = client.put("/customers/test-company", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Customer updated successfully"
        assert data["customer"]["customer_name"] == "Updated Test Company"
        assert data["customer"]["director"] == "New Director"
    
    def test_put_customer_partial_update(self):
        """Test PUT /customers/{id} with partial data."""
        update_data = {
            "director": "Different Director"
        }
        
        response = client.put("/customers/test-company", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["customer"]["director"] == "Different Director"
        assert data["customer"]["customer_name"] == "Test Company"  # Unchanged
    
    def test_put_customer_not_found(self):
        """Test PUT /customers/{id} for non-existent customer."""
        update_data = {
            "director": "Someone"
        }
        
        response = client.put("/customers/non-existent", json=update_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_put_customer_invalid_url(self):
        """Test PUT /customers/{id} rejects malformed URL."""
        update_data = {
            "career_links": [
                {"label": "Bad Link", "url": "not-a-valid-url"}
            ]
        }
        
        response = client.put("/customers/test-company", json=update_data)
        
        assert response.status_code == 422  # Pydantic validation error

