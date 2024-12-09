from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str

# Create a valid User instance
user = User(id=1, name="Alice", email="alice@example.com")

# Attempt to create an invalid User instance
invalid_user = User(id="invalid_id", name=123, email="invalid_email")  # Will raise a ValidationError

# Serialize the valid user to JSON
json_data = user.json()