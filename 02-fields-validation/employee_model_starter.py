from typing import Optional
from pydantic import BaseModel, Field # type: ignore

# TODO: Create Employee model
# Fields:
# - id: int
# - name: str (min 3 chars)
# - department: optional str (default 'General')
# - salary: float (must be >= 10000)


class Employee(BaseModel):
    id: int
    name: str = Field(..., min_length=3, max_length= 10000, description= "Employee Name") # ... means required
    department: Optional[str] = "General"
    salary: float = Field(..., ge=10000, description= "Employee Salary")

emploee = Employee(id=1.1,name="sourav",department="Sales",salary=10000)

print(emploee)
