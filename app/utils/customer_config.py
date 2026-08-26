"""Customer configuration file management."""

import json
import re
from pathlib import Path
from typing import Any


class CustomerConfigManager:
    """Manages reading and writing customer configuration file."""
    
    def __init__(self, config_path: Path | None = None):
        """Initialize config manager with path to customers.json.
        
        Args:
            config_path: Path to customers.json file. Defaults to config/customers.json
                        relative to project root.
        """
        if config_path is None:
            # Default path: project_root/config/customers.json
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "customers.json"
        
        self.config_path = Path(config_path)
    
    def read_config(self) -> list[dict[str, Any]]:
        """Read customers from config file.
        
        Reads the file fresh on each call (no caching).
        
        Returns:
            List of customer dictionaries.
            
        Raises:
            FileNotFoundError: If config file doesn't exist.
            json.JSONDecodeError: If config file contains invalid JSON.
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Validate structure
        if not isinstance(data, dict) or "customers" not in data:
            raise ValueError("Invalid config structure: missing 'customers' key")
        
        if not isinstance(data["customers"], list):
            raise ValueError("Invalid config structure: 'customers' must be a list")
        
        return data["customers"]
    
    def _generate_customer_id(self, customer_name: str) -> str:
        """Generate a stable customer_id slug from customer_name.
        
        Args:
            customer_name: The customer's display name.
            
        Returns:
            Lowercase, hyphenated slug (e.g., "Cisco Systems" -> "cisco-systems").
        """
        # Convert to lowercase, replace spaces and special chars with hyphens
        slug = re.sub(r'[^\w\s-]', '', customer_name.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')
    
    def _validate_customer_unique(self, customer_id: str, existing_customers: list[dict]) -> None:
        """Validate that customer_id is unique.
        
        Args:
            customer_id: The customer ID to check.
            existing_customers: List of existing customer dictionaries.
            
        Raises:
            ValueError: If customer_id already exists.
        """
        existing_ids = {c.get("customer_id") for c in existing_customers}
        if customer_id in existing_ids:
            raise ValueError(
                f"Customer with ID '{customer_id}' already exists. "
                "Please use a different customer name."
            )
    
    def add_customer(
        self,
        customer_name: str,
        director: str,
        bizdev: list[str],
        career_links: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Add a new customer to the config file.
        
        Generates customer_id, validates uniqueness, and writes atomically.
        
        Args:
            customer_name: Customer's display name.
            director: Director name.
            bizdev: List of business development contacts.
            career_links: List of dicts with 'label' and 'url' keys.
            
        Returns:
            The newly created customer dictionary.
            
        Raises:
            ValueError: If customer_id already exists or validation fails.
            FileNotFoundError: If config file doesn't exist.
        """
        # Read existing config
        existing_customers = self.read_config()
        
        # Generate and validate customer_id
        customer_id = self._generate_customer_id(customer_name)
        self._validate_customer_unique(customer_id, existing_customers)
        
        # Create new customer object
        new_customer = {
            "customer_id": customer_id,
            "customer_name": customer_name,
            "director": director,
            "bizdev": bizdev,
            "career_links": career_links,
        }
        
        # Append to existing customers
        updated_customers = existing_customers + [new_customer]
        
        # Write atomically
        self._write_config_atomic({"customers": updated_customers})
        
        return new_customer
    
    def update_customer(
        self,
        customer_id: str,
        customer_name: str | None = None,
        director: str | None = None,
        bizdev: list[str] | None = None,
        career_links: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Update an existing customer in the config file.
        
        Only provided fields will be updated. If customer_name changes and
        generates a different customer_id, validates the new ID is unique.
        
        Args:
            customer_id: The current customer_id to update.
            customer_name: New customer name (optional).
            director: New director name (optional).
            bizdev: New list of business development contacts (optional).
            career_links: New list of career link dicts (optional).
            
        Returns:
            The updated customer dictionary.
            
        Raises:
            ValueError: If customer_id not found or new customer_id already exists.
            FileNotFoundError: If config file doesn't exist.
        """
        # Read existing config
        existing_customers = self.read_config()
        
        # Find the customer to update
        customer_index = None
        current_customer = None
        for i, customer in enumerate(existing_customers):
            if customer.get("customer_id") == customer_id:
                customer_index = i
                current_customer = customer.copy()
                break
        
        if customer_index is None:
            raise ValueError(f"Customer with ID '{customer_id}' not found")
        
        # Update fields if provided
        if customer_name is not None:
            new_customer_id = self._generate_customer_id(customer_name)
            # If customer_id changes, validate uniqueness
            if new_customer_id != customer_id:
                # Check new ID doesn't exist (excluding current customer)
                other_customers = [c for i, c in enumerate(existing_customers) if i != customer_index]
                self._validate_customer_unique(new_customer_id, other_customers)
                current_customer["customer_id"] = new_customer_id
            current_customer["customer_name"] = customer_name
        
        if director is not None:
            current_customer["director"] = director
        
        if bizdev is not None:
            current_customer["bizdev"] = bizdev
        
        if career_links is not None:
            current_customer["career_links"] = career_links
        
        # Replace customer in list
        existing_customers[customer_index] = current_customer
        
        # Write atomically
        self._write_config_atomic({"customers": existing_customers})
        
        return current_customer
    
    def _write_config_atomic(self, data: dict[str, Any]) -> None:
        """Write config data to file atomically.
        
        Writes to a temporary file first, then replaces the original to avoid
        corruption if the process is interrupted mid-write.
        
        Args:
            data: The full config dictionary to write.
        """
        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to temporary file first
        temp_path = self.config_path.with_suffix('.json.tmp')
        
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()  # Ensure data is written to disk
            
            # Atomic replace: rename temp file to actual config file
            temp_path.replace(self.config_path)
        
        except Exception as e:
            # Clean up temp file if write failed
            if temp_path.exists():
                temp_path.unlink()
            raise e
